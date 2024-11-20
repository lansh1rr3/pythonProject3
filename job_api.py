from typing import Dict, List

import requests

API_ENDPOINT = "https://api.hh.ru/vacancies"


def fetch_company_vacancies(
        employer_id: str = None, total_pages: int = 1
) -> List[Dict]:
    vacancies = []
    params = {"per_page": 100}

    if employer_id:
        params["employer_id"] = employer_id

    for page in range(total_pages):
        params["page"] = page
        response = requests.get(API_ENDPOINT, params=params)
        if response.ok:
            items = response.json().get("items", [])
            vacancies.extend(items)
            if len(items) < 100:
                break
        else:
            print(f"Ошибочка: {response.status_code}")
            break

    return vacancies
