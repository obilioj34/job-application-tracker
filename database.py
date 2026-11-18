"""MySQL queries and connection lifetime for the job tracker."""
import os

import mysql.connector
from flask import g


IDS = {
    "companies": "company_id",
    "jobs": "job_id",
    "applications": "application_id",
    "contacts": "contact_id",
}

LIST_QUERIES = {
    "companies": """
        SELECT c.* FROM companies c ORDER BY c.company_name, c.company_id
    """,
    "jobs": """
        SELECT j.*, c.company_name FROM jobs j
        JOIN companies c ON c.company_id = j.company_id
        ORDER BY j.date_posted DESC, j.job_id DESC
    """,
    "applications": """
        SELECT a.*, j.job_title, c.company_name FROM applications a
        JOIN jobs j ON j.job_id = a.job_id
        JOIN companies c ON c.company_id = j.company_id
        ORDER BY a.application_date DESC, a.application_id DESC
    """,
    "contacts": """
        SELECT p.*, c.company_name FROM contacts p
        JOIN companies c ON c.company_id = p.company_id
        ORDER BY p.contact_name, p.contact_id
    """,
}


def get_db():
    if "db" not in g:
        g.db = mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "3306")),
            database=os.getenv("DB_NAME", "job_tracker"),
            user=os.getenv("DB_USER", "job_tracker_app"),
            password=os.getenv("DB_PASSWORD", ""),
            connection_timeout=5,
        )
    return g.db


def close_db(_error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def fetch(sql, params=()):
    with get_db().cursor(dictionary=True) as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def write(sql, params):
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            result = cursor.lastrowid
        connection.commit()
    except mysql.connector.Error:
        connection.rollback()
        raise
    return result


def list_records(table):
    return fetch(LIST_QUERIES[table])


def get_record(table, record_id):
    # Table and column names come from the fixed application schema.
    rows = fetch(f"SELECT * FROM {table} WHERE {IDS[table]} = %s", (record_id,))
    return rows[0] if rows else None


def insert_record(table, values):
    columns = ", ".join(values)
    placeholders = ", ".join(["%s"] * len(values))
    return write(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(values.values()))


def update_record(table, record_id, values):
    assignments = ", ".join(f"{column} = %s" for column in values)
    write(f"UPDATE {table} SET {assignments} WHERE {IDS[table]} = %s", (*values.values(), record_id))


def delete_record(table, record_id):
    write(f"DELETE FROM {table} WHERE {IDS[table]} = %s", (record_id,))
