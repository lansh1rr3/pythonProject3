import configparser

from db_manager import DBManager
from job_api import fetch_company_vacancies

config = configparser.ConfigParser()
config.read("settings.ini")

db_settings = {
    "dbname": config["database"]["dbname"],
    "user": config["database"]["user"],
    "password": config["database"]["password"],
    "host": config["database"]["host"],
}

db = DBManager(db_settings)
db.setup_tables()

vacancies_data = fetch_company_vacancies(total_pages=5)

for data in vacancies_data:
    company = data.get("employer", {}).get("name", "Unknown Company")
    title = data.get("name", "No Title")
    salary = data.get("salary", {})
    min_salary = salary.get("from") if salary else None
    max_salary = salary.get("to") if salary else None
    link = data.get("alternate_url", "No Link")

    company_id = db.add_company(company)
    db.add_vacancy(title, min_salary, max_salary, link, company_id)

while True:
    print("\nВыберите вариант:")
    print("1. Список вакансий")
    print("2. Вакансии по компаниям")
    print("3. Средняя зарплата")
    print("4. Поиск вакансий по ключевому слову")
    print("5. Вакансии с зарплатой выше средней")

    user_input = input("Ваш выбор: ")

    if user_input == "1":
        for vac in db.get_all_vacancies():
            print(
                f"Вакансия: {vac[0]}, От: {vac[1]} до {vac[2]}, Ссылка: {vac[3]}, Компания: {vac[4]}"
            )
    elif user_input == "2":
        for company in db.get_vacancy_count_by_company():
            print(f"Компания: {company[0]}, Вакансий: {company[1]}")
    elif user_input == "3":
        print(f"Средняя зарплата: {db.get_average_salary():.2f}")
    elif user_input == "4":
        keyword = input("Введите слово для поиска: ")
        for vac in db.search_vacancies(keyword):
            print(
                f"Вакансия: {vac[0]}, От: {vac[1]} до {vac[2]}, Ссылка: {vac[3]}, Компания: {vac[4]}"
            )
    elif user_input == "5":
        avg_salary = db.get_average_salary()
        for vac in db.get_high_salary_vacancies(avg_salary):
            print(
                f"Вакансия: {vac[0]}, От: {vac[1]} до {vac[2]}, Ссылка: {vac[3]}, Компания: {vac[4]}"
            )
