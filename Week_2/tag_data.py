import sqlite3
import time
import os
from dotenv import load_dotenv
from pathlib import Path
from prompt_model import prompt_model


BASE_DIR = Path(__file__).parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

GEMINI_MODEL = "gemini-2.5-flash-lite"
BATCH_SIZE = 5
MAX_RETRIES = 3
RETRY_WAIT = 8  # seconds

#split list into chunks
def chunked(first, size):
    for i in range(0, len(first), size):
        yield first[i:i + size]

# ── Helper: estimate tokens (since prompt_model doesn't return count) ─
def estimate_tokens(text: str) -> int:
    # Task says: assume 4 tokens per word if model doesn't return count
    return len(text.split()) * 4

# --------------Parse AI reply into jobs-------------------------
def parse_reply(reply: str):
    results = {}    # kita buat empty dictionary dulu 
    for line in reply.splitlines(): # split reply into lines
        line = line.strip() # remove extra spaces
        if not line or ":" not in line: # kalau takde colon, skip
            continue

        clean = line.replace("JOB", "").replace("Job ", "") # buang "JOB" atau "Job " kalau ada, supaya tinggal ID dan tech stack
        parts = clean.split(":", 1) # sume before colon is job ID, rest is tech stack
        raw_id = parts[0].strip()
        tech_stack = parts[1].strip() if len(parts) > 1 else ""

        try:
            job_id = int(raw_id)
            if tech_stack:
                results[job_id] = tech_stack
        except ValueError:
            print(f"Skipping invalid job ID: {raw_id}")
            continue
            
    return results

# --------------Main function-------------------------
def tag_data(db_url: str):
    total_input_tokens = 0
    total_output_tokens = 0
    start_time = time.time()
    print(f"Using model: [{GEMINI_MODEL}] via prompt_model.py\n")
    
    # connect to db
    try:
        conn = sqlite3.connect(db_url)
        cursor = conn.cursor()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return 0,0,0
    
    # fetch rows that need tagging
    try:
        cursor.execute("""
            SELECT source_id, description 
            FROM jobs
            WHERE tech_stack IS NULL
        """)
        rows = cursor.fetchall()
    except Exception as e:
        print(f"Error fetching data from database: {e}")
        conn.close()
        return 0,0,0
    
    if not rows:
        print("No rows found that need tagging.")
        elapsed = (time.time() - start_time) * 1000
        print(f"Total tokens used: 0, took {elapsed:.3f}ms")
        conn.close()
        return 0,0,0
    
    print(f"Found {len(rows)} jobs to tag using [{GEMINI_MODEL}]...\n")

    # process in batches
    for batch_num, batch in enumerate(chunked(rows, BATCH_SIZE)):
        prompt_lines = [
            "You are a technical skills extractor.",
             "For each job description below, extract ONLY the technical skills,",
             "tools, frameworks, and programming languages explicitly mentioned.",
             "",
             "Reply in EXACTLY this format — one line per job, nothing else:",
             "JOB <id>: skill1, skill2, skill3",
             "",
             "Example:",
             "JOB 11111: Python, SQL, Docker, AWS",
             "JOB 22222: Java, Spring Boot, PostgreSQL",
             "",
             "Jobs:",
             "---",
        ]

        for source_id, description in batch:
            short_desc = (description or "")[:4000]  
            prompt_lines.append(f"JOB {source_id}: {short_desc}")
            prompt_lines.append("---")

        prompt_lines.append("\nReply with ONLY the JOB lines. No extra text, no explanation.")
        prompt = "\n".join(prompt_lines)

        # Count input tokens (estimated since prompt_model doesn't return count)
        total_input_tokens += estimate_tokens(prompt)

        # --retry loop--
        success = False
        for attempt in range(1, MAX_RETRIES + 1):
            reply = prompt_model(GEMINI_MODEL, prompt)

            # Check if reply is None (API error) or returned an error string
            if reply is None or reply.startswith("[ERROR]"):
                print(f"[Batch {batch_num}] Attempt {attempt} failed.")
                if attempt < MAX_RETRIES:
                    wait_time = 60 if reply is None else RETRY_WAIT
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                continue

            # Count output tokens (estimated)
            total_output_tokens += estimate_tokens(reply)

            # Parse the reply
            results = parse_reply(reply)
            if not results:
                print(f"[Batch {batch_num}] Attempt {attempt} failed to parse any valid job tags.")
                if attempt < MAX_RETRIES:
                    print(f"Retrying in {RETRY_WAIT} seconds...")
                time.sleep(RETRY_WAIT)
                continue # Try the next attempt

            # save results to db
            for source_id , _ in batch:
                job_id = int(source_id)
                if job_id in results:
                    tech_stack = results[job_id]
                    try:
                        cursor.execute("""
                        UPDATE jobs
                        SET tech_stack = ?
                        WHERE source_id = ?
                    """, (tech_stack, job_id))
                        print(f"Analyzed Job {job_id}: {tech_stack}")
                    except Exception as e:
                        print(f"Error updating database for job {job_id}: {e}")
                else:
                    print(f"Warning: No tags found for job {job_id} in Gemini reply.")
        
            try:
                conn.commit()
            except Exception as e:
                print(f"Error committing changes to database: {e}")
            
            success = True
            print(f"[Batch {batch_num}] Successfully tagged {len(results)} jobs...")
            
            break

        if not success:
            print(f"[Batch {batch_num}] Failed after {MAX_RETRIES} attempts. Moving to next batch.")
            continue

        time.sleep(4)  # brief pause between batches to avoid rate limits

    conn.close()

    #summary
    elapsed = (time.time() - start_time) * 1000
    total_tokens = total_input_tokens + total_output_tokens
    print(f"\nTagging completed. Total tokens used: {total_tokens}, took {elapsed:.3f}ms")
    return total_input_tokens, total_output_tokens, elapsed

if __name__ == "__main__":    
    db_url = "data/resources/jobs_d1.db"
    tag_data(db_url)


            
