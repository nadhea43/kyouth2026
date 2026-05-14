# Job Listings Data Pipeline

A local ETL (Extract, Transform, Load) data engineering pipeline that processes raw job listing .mhtml files through a Medallion Architecture — from raw source to a clean, queryable SQLite database.

[0_source] → [1_bronze] → [2_silver] → [3_gold/jobs.db]
______________________________________________________________________________________________________

## Project Description

This pipeline ingests raw .mhtml job listing files, extracts and cleans their HTML content, parses structured job fields, and stores them in a relational SQLite database (jobs.db). A data profiling report is also generated to summarise the quality and distribution of the loaded data.

The pipeline is broken into four modules:
Module 1 -> ingestor.py         -> Bronze -> Extract HTML from .mhtml source files
Module 2 -> processor.py        -> Silver -> Parse job fields from HTML into JSON
Module 3 -> loader.py           -> Gold   -> Load JSON records into SQLite database
Module 4 -> run_data_profile.py -> Gold   -> Profile and aggregate database contents

The database schema for jobs.db:
source_id | job_title | company | description | tech_stack
________________________________________________________________________________________________________

## Setup Instructions

Prerequisites:
Python 3.14.x
uv version 0.8.x

Installation:

Clone the repository:

bash   git clone <https://github.com/nadhea43/kyouth2026.git>


Install dependencies using uv:

bash   uv sync
__________________________________________________________________________________________________________
## Usage:

main.py is the single entry point for the entire pipeline. It accepts a subcommand to run a specific module or the full pipeline.
Commands
python main.py ingest      # Module 1: Extract HTML from .mhtml source files → 1_bronze/
python main.py process     # Module 2: Parse job fields from HTML → 2_silver/
python main.py load        # Module 3: Load JSON records into SQLite → 3_gold/jobs.db
python main.py profile     # Module 4: Run data profile report on the database
python main.py all         # Run all modules in sequence (end-to-end)
__________________________________________________________________________________________________________
## Project Folder

week1/
├── data/
│   ├── 0_source/          # Vendor Data: Unedited MHTML
│   │   ├── <TITLE_0>.mhtml
│   │   └── <TITLE_1>.mhtml
│   ├── 1_bronze/          # Raw Data: Decoded HTML
│   │   ├── <TITLE_0>.html
│   │   └── <TITLE_1>.html
│   ├── 2_silver/          # Clean Data: Removed HTML tags
│   │   ├── <TITLE_0>.json
│   │   └── <TITLE_1>.json
│   └── 3_gold/            # Final Warehouse: SQLite DB
│       └── jobs.db
├── src/
│   ├── ingestor.py        # Day 1: Extracts to data/1_bronze/
│   ├── processor.py       # Day 2: Cleans/Validates to data/2_silver/
│   ├── loader.py          # Day 3: Loads to data/3_gold/
│   └── profiler.py        # Day 4: Quality checks on Gold layer
├── main.py                # CLI Orchestrator (The Conductor)
├── pyproject.toml         # Environment & Dependencies (using `uv`)
├── uv.lock
└── README.md
__________________________________________________________________________________________________________
## Technical Reflections:

### Module 1: The Extractor (Medallion & Lakehouses)
Why is it useful to keep the original raw HTML files instead of directly inserting processed data into the database? What problems become easier to debug or recover from?
- **Answer**: It is easier to debug if problem arises. For example if extracting any incorrect field, we can directly fix on the processor.py without need to re run the original .mthml souces. The HTML acting like safety copies because without it being saved means we need to starting all over again from beginning

### Module 2: Treatment Plant (ETL vs ELT & Scale)
Why do cloud systems prefer loading raw data first before cleaning it (ELT)? What problems happen when processing files sequentially, and how does distributed processing help?
- **Answer**: Because raw storage is cheap hence it is better to load all the data first then using the cloud's powerful computers to clean it. In this project we're using ETL which data is transform first before load in seqeuntial because files are processed one at a time. It is okey for small scale but it will take longer time for larger dataset because it blocks to proceed with the next file if one file still not finished. Therefore, distributed processing tools like Apache Spark solve this by splitting the workload across many machines in parallel which reduce the processing time for large dataset because many files can run at the same time.

### Module 3: The Blueprint & The Vault (Storage & Contracts)
 What should happen if an important field like job_title disappears? Why fail early instead of silently inserting nulls into DB? How does INSERT OR IGNORE help prevent duplicate records?
 - **Answer**: if important field like job_title disappears fail early should be implement to prevent the data quality issues. Silently inserting into DB is dangerous as it can corrupts analytic and break reports later hence early action is needed so that easier to fix rather than letting bad data propagate silently in thorough the system. INSERT OR IGNORE help by prevent creation of same records again. For example, when we want to re run the system, the database will check for the existing record to avoid duplication. 

 ### Module 4: The QA Inspector & Orchestrator (Orchestration & DAGs)
 What happens if processor.py crashes halfway? How are automated orchestration tools more reliable than manual retries with Python scripts?
 - **Answer**: If processor.py crashes halfway, our main.py orchestration has no automatic way to know where it stops. So, whe need figure out ourself and manually re-run. Tools like Apache Airflow model pipelines as Directed Acyclic Graphs(DAGs) is like a smart manager who tracks every step. If one of the steps fails, it automatically retries it, notifies us and resume from the failed step without touching the successfull task. It also keeps a full log of what ran, when, and whether it passed or failed. At production scale, DAG is much more better for reliability and observability.