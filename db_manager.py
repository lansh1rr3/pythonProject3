import requests
import psycopg2
from typing import Optional, Any, List
from concurrent.futures import ThreadPoolExecutor
import configparser

BASE_URL = "https://api.hh.ru/"


class DBManager:
    def __init__(self, db_connection_params):
        self.connection = psycopg2.connect(**db_connection_params)
        self.cursor = self.connection.cursor()

    def insert_company(self, company_name: str, industry: Optional[str] = None, area: Optional[str] = None) -> int:
        self.cursor.execute(
            "INSERT INTO companies (name, industry, area) VALUES (%s, %s, %s) ON CONFLICT (name) DO NOTHING RETURNING id",
            (company_name, industry, area))
        self.connection.commit()
        result = self.cursor.fetchone()
        return result[0] if result else self.get_company_id(company_name)

    def get_company_id(self, company_name: str) -> int:
        self.cursor.execute("SELECT id FROM companies WHERE name = %s", (company_name,))
        return self.cursor.fetchone()[0]

    def insert_vacancies_bulk(self, vacancies: List[tuple]):
        self.cursor.executemany(
            "INSERT INTO vacancies (title, salary_min, salary_max, url, company_id) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (url) DO NOTHING",
            vacancies)
        self.connection.commit()

    def get_companies_and_vacancies_count(self) -> List[tuple[Any, ...]]:
        self.cursor.execute(
            "SELECT c.name, COUNT(v.id) FROM companies c LEFT JOIN vacancies v ON c.id = v.company_id GROUP BY c.id ORDER BY COUNT(v.id) DESC LIMIT 10")
        return self.cursor.fetchall()

    def get_all_vacancies(self) -> List[tuple[Any, ...]]:
        self.cursor.execute(
            "SELECT v.title, v.salary_min, v.salary_max, v.url, c.name FROM vacancies v JOIN companies c ON v.company_id = c.id")
        return self.cursor.fetchall()

    def get_avg_salary(self) -> Optional[float]:
        self.cursor.execute(
            "SELECT AVG((COALESCE(v.salary_min, 0) + COALESCE(v.salary_max, 0)) / 2.0) FROM vacancies v WHERE v.salary_min IS NOT NULL OR v.salary_max IS NOT NULL")
        return self.cursor.fetchone()[0]

    def get_vacancies_with_higher_salary(self) -> List[tuple[Any, ...]]:
        avg_salary = self.get_avg_salary()
        if not avg_salary: return []
        self.cursor.execute(
            "SELECT v.title, COALESCE(v.salary_min, 0), COALESCE(v.salary_max, 0), v.url, c.name FROM vacancies v JOIN companies c ON v.company_id = c.id WHERE ((COALESCE(v.salary_min, 0) + COALESCE(v.salary_max, 0)) / 2.0) > %s",
            (avg_salary,))
        return self.cursor.fetchall()

    def get_vacancies_with_keyword(self, keyword: str) -> List[tuple[Any, ...]]:
        self.cursor.execute(
            "SELECT v.title, v.salary_min, v.salary_max, v.url, c.name FROM vacancies v JOIN companies c ON v.company_id = c.id WHERE v.title ILIKE %s",
            ('%' + keyword + '%',))
        return self.cursor.fetchall()

    def close_connection(self):
        self.cursor.close()
        self.connection.close()


def get_vacancies_for_company(company_id=None, pages=1):
    all_vacancies = []
    params = {'employer_id': company_id, 'per_page': 100} if company_id else {'per_page': 100}
    for page in range(pages):
        response = requests.get(f"{BASE_URL}vacancies", params={**params, 'page': page})
        if response.status_code == 200:
            items = response.json().get('items', [])
            all_vacancies.extend(items)
            if len(items) < 100: break
        else:
            print(f"Ошибка при получении данных: {response.status_code}")
            break
    return all_vacancies


def get_all_vacancies_for_companies(companies, db):
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_vacancies_for_company, company['id'], 5): company for company in companies}
        for future in futures:
            company = futures[future]
            company_name, industry, area = company['name'], company.get('industry'), company.get('area')
            try:
                vacancies = future.result()
                if vacancies:
                    company_id = db.insert_company(company_name, industry, area)
                    vacancies_data = [(vacancy.get('name', 'Не указано'), vacancy.get('salary', {}).get('from'),
                                       vacancy.get('salary', {}).get('to'), vacancy.get('alternate_url', 'Нет ссылки'),
                                       company_id) for vacancy in vacancies]
                    db.insert_vacancies_bulk(vacancies_data)
                    print(f"Вакансии для {company_name} добавлены.")
            except Exception as e:
                print(f"Ошибка при получении данных для {company_name}: {e}")


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('database.ini')
    connection_params = {key: config['database'][key] for key in ['dbname', 'user', 'password', 'host']}

    db_manager = DBManager(connection_params)
    employers = [{'id': '1', 'name': 'Компания 1', 'industry': 'IT', 'area': 'Moscow'},
                 {'id': '2', 'name': 'Компания 2', 'industry': 'Finance', 'area': 'Saint Petersburg'}]

    get_all_vacancies_for_companies(employers, db_manager)
    db_manager.close_connection()
