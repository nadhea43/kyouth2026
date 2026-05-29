import sqlite3
import json
from pathlib import Path


def init_db(db_path):

    # open database file, kalau belum exist then sqlite akan auto create
    connection = sqlite3.connect(db_path)

    # cursor ni mcm pen in database where write(execute) sql commands throtugh sini
    cursor = connection.cursor()

    # create table kalau belum ada
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs(
                   source_id    TEXT PRIMARY KEY,
                   job_title    TEXT,
                   company      TEXT,
                   description  TEXT,
                   tech_stack   TEXT
                   )
   """)

    connection.commit()

    print("Database initiliazed: jobs table is ready")
    return connection


def insert_jobs(cursor, data):
    cursor.execute(
        """
        INSERT OR IGNORE INTO jobs (source_id, job_title, company, description, tech_stack)
        VALUES(?, ?, ?, ?, ?)
   """,
        (
            data.get("source_id"),
            data.get("job_title"),
            data.get("company"),
            data.get("description"),
            data.get("tech_stack"),
        ),
    )

    # kira how many rowa affected, if it is duplicate then rowcpunt=0, if new row insert then rowcount=1
    return cursor.rowcount == 1


# main function to baca json file n load dlam daatabase
def load_all_jsons(input_dir, output_dir):
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    print(" Gold: Loading Silver data into the database...")

    # create output folder, kalau dah exist then its ok
    output_path.mkdir(parents=True, exist_ok=True)

    # define kat mana database file akan diletakkan
    db_path = output_path / "jobs.db"

    # connect to database
    connection = init_db(db_path)
    cursor = connection.cursor()

    if not input_path.exists:
        print(f"input directory not found: {input_dir}")
        connection.close()
        return

    total = 0
    inserted = 0
    skipped = 0

    json_files = list(input_path.glob("*.json"))

    for jsonFile in json_files:
        jsonFileName = jsonFile.name

        # baca JSON file
        try:
            with open(jsonFile, "r", encoding="utf=8") as f:
                data = json.load(f)  # parse JSON text into a python dictionary

        except (json.JSONDecodeError, IOError) as e:
            print(f"Failed to read {jsonFileName}: {e}")
            total += 1
            continue  # skip to next file

        total += 1
        was_inserted = insert_jobs(cursor, data)

        if was_inserted:
            inserted += 1
            print(f" Inserted: {jsonFileName}")
        else:
            skipped += 1
            print(f" Skipped: {jsonFileName}")

    connection.commit()  # save dalam db
    connection.close()  # close db when done

    print(f" Gold Summary: Total: {total} | Inserted: {inserted} | Skipped: {skipped}")
