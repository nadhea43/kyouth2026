from pathlib import Path  # Figure out why use Path?
from src.ingestor import ingest_all_mhtml
from src.processor import process_all_html
from src.loader import load_all_jsons
from src.run_data_profile import run_data_profile
import sys

SOURCE_DIR = Path("data/0_source")
BRONZE_DIR = Path("data/1_bronze")
SILVER_DIR = Path("data/2_silver")
GOLD_DIR = Path("data/3_gold")
DB_NAME = "jobs.db"


def run_profiler():
    db_path = GOLD_DIR / DB_NAME
    run_data_profile(db_path)


def run_gold():
    input_dir = SILVER_DIR
    output_dir = GOLD_DIR
    load_all_jsons(input_dir, output_dir)


def run_silver():
    input_dir = BRONZE_DIR
    output_dir = SILVER_DIR
    process_all_html(input_dir, output_dir)


def run_bronzer():
    input_dir = SOURCE_DIR
    output_dir = BRONZE_DIR
    ingest_all_mhtml(input_dir, output_dir)


def main():
    if len(sys.argv) < 2:
        print("Week_1 python main.py")
        print("Usage: python main.py <command>")
        print("commands: ingest, process, load, profile, all")
        return

    command = sys.argv[1]

    if command == "ingest":
        print(" Running Ingesting")
        run_bronzer()
    elif command == "process":
        print(" Running Processing")
        run_silver()
    elif command == "load":
        print(" Running Loading")
        run_gold()
    elif command == "profile":
        print(" Running Profiling")
        run_profiler()
    elif command == "all":
        print(" Running full pipline")
        print("\n Steps 1/4: Ingesting Data....")
        run_bronzer()
        print("\n Steps 2/4: Processing Data....")
        run_silver()
        print("\n Steps 3/4: Loading data into Database....")
        run_gold()
        print("\n Steps 4/4: Runnig data profile....")
        run_profiler()
        print("\n Full pipeline complete")
    else:
        print("unkwon")


if __name__ == "__main__":
    main()
