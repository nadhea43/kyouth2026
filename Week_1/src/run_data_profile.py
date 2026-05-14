import sqlite3
from pathlib import Path

def run_data_profile(db_path):
    database_path = Path(db_path)

    if not database_path.exists:
        print(f"Database not found at{database_path} ")
        return

    # connect database
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()    # hand that run the sql

    # cari total number of row
    cursor.execute("""
        SELECT COUNT (*) FROM jobs        
    """)
    total_record = cursor.fetchone()[0]

    # cari Null values in job_title, company, or description
    cursor.execute("""
        SELECT
        SUM(CASE WHEN job_title IS NULL THEN 1 ELSE 0 END),
        SUM(CASE WHEN company IS NULL THEN 1 ELSE 0 END),
        SUM(CASE WHEN description IS NULL THEN 1 ELSE 0 END)
        FROM jobs           
    """)
    null_rows = cursor.fetchone()
    null_job_title = null_rows[0] or 0
    null_company = null_rows[1] or 0
    null_desctiption = null_rows[2] or 0

    # cari Average description length
    cursor.execute("""
        SELECT AVG(LENGTH(description)) FROM jobs
        WHERE description IS NOT NULL
    """)
    Average_description = int(cursor.fetchone()[0])

    # cari shortest description length with source_id and job_title
    cursor.execute("""
        SELECT LENGTH(description), source_id, job_title FROM jobs
        WHERE description IS NOT NULL
        ORDER BY LENGTH(description) ASC
        LIMIT 1 
    """)
    shortest_row = cursor.fetchone()
    shortest_description_length = shortest_row[0]
    shortest_source_id = shortest_row[1]
    shortest_job_title = shortest_row[2]

    # cari longest description length with source_id and job_title
    cursor.execute("""
        SELECT LENGTH(description), source_id, job_title FROM jobs
        WHERE description IS NOT NULL
        ORDER BY LENGTH(description) DESC
        LIMIT 1
    """)
    longest_row = cursor.fetchone()
    longest_description_length = longest_row[0]
    longest_source_id = longest_row[1]
    longest_job_title = longest_row[2]

    connection.close()

    # print report
    print(" --- Data Quality Report ----")
    print(f" Total Records: {total_record}")
    print(f" Missing Values -> job_title: {null_job_title}, company: {null_company}, description: {null_desctiption} ")
    print(f" Avg Description Length: {Average_description}")
    print(f" Shortest Description: {shortest_description_length} chars")
    print(f" ↳ source_id: {shortest_source_id} | job_title: {shortest_job_title}")
    print(f" Longest Description: {longest_description_length} chars")
    print(f" ↳ source_id: {longest_source_id}  | job_title: {longest_job_title} ")



