import sqlite3
import time
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_MODEL = "gemini-2.5-flash"
BATCH_SIZE = 5
MAX_RETRIES = 3
RETRY_WAIT = 5  # seconds

def chunked(first, size):
    for i in range(0, len(first), size):
        yield first[i:i + size]

# --------------call GEMINI-------------------------
def call_gemini(model, prompt: str):
    try:
        response = model.generate_content(prompt)
        reply = response.text

        # get token usage
        input_tokens = 0    # Length of our question
        output_tokens = 0   # Length of the AI answer
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            input_tokens = response.usage_metadata.prompt_tokens_count or 0
            output_tokens = response.usage_metadata.candidates_tokens_count or 0

        # fallback
        if input_tokens == 0:
            input_tokens = len(prompt.split()) * 4
        if output_tokens == 0:
            output_tokens = len(reply.split()) * 4

        return reply, input_tokens, output_tokens 
    
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return None, 0, 0

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

    # setup gemini
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found in environment variables.")
        return 0,0,0
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
    except Exception as e:
        print(f"Error configuring Gemini API: {e}")
        return 0,0,0
    
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
            short_desc = (description or "")[:700]  # take first 700 chars for context
            prompt_lines.append(f"JOB {source_id}: {short_desc}")
            prompt_lines.append("---")

        prompt_lines.append("\nReply with ONLY the JOB lines. No extra text, no explanation.")
        prompt = "\n".join(prompt_lines)

        # --retry loop--
        success = False
        for attempt in range(1, MAX_RETRIES + 1):
            reply, input_tokens, output_tokens = call_gemini(model, prompt)

        # if Gemini returned an error string
        if reply.startswith("[ERROR]"):
            print(f"[Batch {batch_num}] Attempt {attempt} failed with error: {reply}")
            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_WAIT} seconds...")
                time.sleep(RETRY_WAIT)
            continue
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens

        # parse the reply to clean replt tu
        results = parse_reply(reply)
        batch_ids = [int(row[0]) for row in batch]
        if not results:
            print(f"[Batch {batch_num}] Attempt {attempt} failed to parse any valid job tags.")
            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_WAIT} seconds...")
                time.sleep(RETRY_WAIT)
            continue

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
                except Exception as e:
                    print(f"Error updating database for job {job_id}: {e}")
            else:
                print(f"Warning: No tags found for job {job_id} in Gemini reply.")
        
        try:
            conn.commit()
        except Exception as e:
            print(f"Error committing changes to database: {e}")
        
        success = True
        print(f"[Batch {batch_num}] Successfully tagged {len(results)} jobs. Input tokens: {input_tokens}, Output tokens: {output_tokens}")
        break  # exit retry loop on success

        if not success:
            print(f"[Batch {batch_num}] Failed after {MAX_RETRIES} attempts. Moving to next batch.")

            
