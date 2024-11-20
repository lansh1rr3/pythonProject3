from typing import Optional

import psycopg2


class DBManager:
    def __init__(self, config: dict):
        self.connection = psycopg2.connect(**config)
        self.cursor = self.connection.cursor()

    def setup_tables(self):
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS companies (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        );
        """
        )
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS vacancies (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            salary_min INTEGER,
            salary_max INTEGER,
            url TEXT,
            company_id INTEGER,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        );
        """
        )
        self.connection.commit()

    def add_company(self, name: str) -> int:
        self.cursor.execute(
            """
        INSERT INTO companies (name) VALUES (%s)
        ON CONFLICT (name) DO NOTHING RETURNING id;
        """,
            (name,),
        )
        self.connection.commit()
        result = self.cursor.fetchone()
        return result[0] if result else self.get_company_id(name)

    def get_company_id(self, name: str) -> Optional[int]:
        self.cursor.execute("SELECT id FROM companies WHERE name = %s;", (name,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def add_vacancy(
            self,
            title: str,
            min_salary: Optional[int],
            max_salary: Optional[int],
            url: str,
            company_id: int,
    ):
        self.cursor.execute(
            """
        INSERT INTO vacancies (title, salary_min, salary_max, url, company_id) 
        VALUES (%s, %s, %s, %s, %s);
        """,
            (title, min_salary, max_salary, url, company_id),
        )
        self.connection.commit()

    def get_all_vacancies(self):
        self.cursor.execute(
            """
        SELECT v.title, v.salary_min, v.salary_max, v.url, c.name
        FROM vacancies v
        JOIN companies c ON v.company_id = c.id;
        """
        )
        return self.cursor.fetchall()

    def get_vacancy_count_by_company(self):
        self.cursor.execute(
            """
        SELECT c.name, COUNT(v.id) 
        FROM companies c
        LEFT JOIN vacancies v ON c.id = v.company_id
        GROUP BY c.name;
        """
        )
        return self.cursor.fetchall()

    def get_average_salary(self) -> Optional[float]:
        self.cursor.execute(
            """
        SELECT AVG((salary_min + salary_max) / 2)
        FROM vacancies
        WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL;
        """
        )
        result = self.cursor.fetchone()
        return result[0] if result else None

    def search_vacancies(self, keyword: str):
        self.cursor.execute(
            """
        SELECT v.title, v.salary_min, v.salary_max, v.url, c.name
        FROM vacancies v
        JOIN companies c ON v.company_id = c.id
        WHERE v.title ILIKE %s;
        """,
            (f"%{keyword}%",),
        )
        return self.cursor.fetchall()

    def get_high_salary_vacancies(self, avg_salary: float):
        self.cursor.execute(
            """
        SELECT v.title, v.salary_min, v.salary_max, v.url, c.name
        FROM vacancies v
        JOIN companies c ON v.company_id = c.id
        WHERE (salary_min + salary_max) / 2 > %s;
        """,
            (avg_salary,),
        )
        return self.cursor.fetchall()

    def close(self):
        self.cursor.close()
        self.connection.close()
