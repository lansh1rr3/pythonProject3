import requests
from concurrent.futures import ThreadPoolExecutor
import time
from typing import List, Dict, Optional

BASE_URL = "https://api.hh.ru/"


def fetch_vacancies(company_id: Optional[str] = None, pages: int = 1) -> List[Dict]:
    """
    Получает вакансии для заданной компании или для всех компаний (если company_id не задан)
    """
    all_vacancies = []
    params = {'employer_id': company_id, 'per_page': 100} if company_id else {'per_page': 100}
    url = f"{BASE_URL}vacancies"

    for page in range(pages):
        params['page'] = page
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            all_vacancies.extend(data.get('items', []))
            if len(data.get('items', [])) < 100:
                break
        else:
            print(f"Ошибка при получении данных о вакансиях: {response.status_code}")
            break

    return all_vacancies


def fetch_vacancies_for_companies(companies: List[Dict], pages: int = 5) -> Dict[str, List[Dict]]:
    """
    Получает вакансии для списка компаний с использованием многозадачности.
    """
    all_vacancies = {}
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(fetch_vacancies, company['id'], pages): company['name']
            for company in companies
        }

        for future in futures:
            company_name = futures[future]
            try:
                vacancies = future.result()
                if vacancies:
                    all_vacancies[company_name] = vacancies
            except Exception as e:
                print(f"Ошибка при получении данных для компании {company_name}: {e}")

    execution_time = round(time.time() - start_time, 2)
    print(f"Время выполнения: {execution_time} секунд")

    return all_vacancies


def calculate_avg_salary(vacancies: List[Dict]) -> float:
    """
    Рассчитывает среднюю зарплату по списку вакансий.
    """
    total_salary = 0
    count = 0

    for vacancy in vacancies:
        salary = vacancy.get('salary')
        if salary:
            salary_min = salary.get('from', 0)
            salary_max = salary.get('to', 0)
            total_salary += (salary_min + salary_max) / 2 if salary_min and salary_max else max(salary_min, salary_max)
            count += 1

    return total_salary / count if count else 0


def filter_vacancies_by_salary(vacancies: Dict[str, List[Dict]], avg_salary: float) -> Dict[str, List[Dict]]:
    """
    Фильтрует вакансии с зарплатой выше средней.
    """
    higher_salary_vacancies = {}
    for company_name, company_vacancies in vacancies.items():
        higher_vacancies = [
            vacancy for vacancy in company_vacancies
            if vacancy.get('salary') and
               (vacancy['salary'].get('from', 0) + vacancy['salary'].get('to', 0)) / 2 > avg_salary
        ]
        if higher_vacancies:
            higher_salary_vacancies[company_name] = higher_vacancies

    return higher_salary_vacancies


def search_vacancies_by_keyword(vacancies: Dict[str, List[Dict]], keyword: str) -> Dict[str, List[Dict]]:
    """
    Ищет вакансии по ключевому слову в названии вакансии.
    """
    keyword = keyword.lower()
    matching_vacancies = {
        company_name: [
            vacancy for vacancy in company_vacancies
            if keyword in vacancy.get('name', '').lower()
        ]
        for company_name, company_vacancies in vacancies.items()
    }

    return matching_vacancies
