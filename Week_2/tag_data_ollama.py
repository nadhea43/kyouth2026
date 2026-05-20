import sqlite3
import time
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# ── Config — change this to swap models easily ──────────────────────
OLLAMA_MODEL = "llama3.1"        # or "phi3" or "deepseek-r1:1.5b"
OLLAMA_URL   = "http://localhost:11434/api/generate"
BATCH_SIZE   = 5
MAX_RETRIES  = 3
RETRY_WAIT   = 3                 # seconds to wait between retries


# ── Helper: split list into chunks ──────────────────────────────────
# Analogy: cutting a loaf of bread into 5-slice portions
def chunked(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


# ── Helper: call Ollama ──────────────────────────────────────────────
def call_ollama(prompt: str) -> str:
    """
    Sends a prompt to the local Ollama server.
    Returns the text response, or an error string (never crashes).
    """
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False      # wait for full response
            },
            timeout=120              # local models can be slow
        )
        data = response.json()
        return data.get("response", "")

    except Exception as e:
        return f"[ERROR] {e}"


# ── Helper: estimate tokens (4 tokens per word) ──────────────────────
# Ollama doesn't always return token counts, so we estimate
def estimate_tokens(text: str) -> int:
    return len(text.split()) * 4


# ── Main function ────────────────────────────────────────────────────
def tag_data(db_url: str):

    total_input_tokens  = 0
    total_output_tokens = 0
    start_time = time.time()

    # Step 1: Connect to database
    try:
        conn   = sqlite3.connect(db_url)
        cursor = conn.cursor()
    except Exception as e:
        print(f"[ERROR] Cannot open database: {e}")
        return 0, 0, 0

    # Step 2: Find all rows where tech_stack is empty
    try:
        cursor.execute("""
            SELECT source_id, description
            FROM jobs
            WHERE tech_stack IS NULL OR tech_stack = ''
        """)
        rows = cursor.fetchall()
    except Exception as e:
        print(f"[ERROR] Cannot read from database: {e}")
        conn.close()
        return 0, 0, 0

    # Nothing to do
    if not rows:
        print("No data to tag")
        elapsed = (time.time() - start_time) * 1000
        print(f"Total tokens used: 0, took {elapsed:.3f}ms")
        conn.close()
        return 0, 0, elapsed

    print(f"Found {len(rows)} jobs to tag using [{OLLAMA_MODEL}]...\n")

    # Step 3: Process in batches
    for batch_num, batch in enumerate(chunked(rows, BATCH_SIZE)):

        # ── Build the prompt ─────────────────────────────────────────
        # We tell the AI exactly what format to reply in
        # so our code can reliably parse it
        prompt_lines = [
            "You are a technical skills extractor.",
            "For each job below, extract ONLY the technical skills, tools, and programming languages mentioned.",
            "Reply in EXACTLY this format, one line per job, nothing else:",
            "JOB_ID: skill1, skill2, skill3",
            "",
            "Example:",
            "12345: Python, SQL, Docker",
            "67890: Java, Spring Boot, AWS",
            "",
            "Jobs to analyze:",
            "---"
        ]

        for source_id, description in batch:
            # Truncate long descriptions to save time & tokens
            short_desc = (description or "")[:600]
            prompt_lines.append(f"JOB {source_id}:\n{short_desc}")
            prompt_lines.append("---")

        prompt_lines.append("\nNow reply with ONLY the JOB_ID: skills lines, no extra text.")
        prompt = "\n".join(prompt_lines)

        total_input_tokens += estimate_tokens(prompt)

        # ── Retry loop ───────────────────────────────────────────────
        success = False

        for attempt in range(1, MAX_RETRIES + 1):
            reply = call_ollama(prompt)

            if reply.startswith("[ERROR]"):
                print(f"[Batch {batch_num}] Attempt {attempt} failed: {reply}")
                time.sleep(RETRY_WAIT)
                continue

            total_output_tokens += estimate_tokens(reply)

            # ── Parse the reply ──────────────────────────────────────
            # We expect lines like:   JOB 91397216: Python, SQL, Java
            # or sometimes just:      91397216: Python, SQL, Java
            results = {}

            for line in reply.splitlines():
                line = line.strip()
                if not line or ":" not in line:
                    continue

                # Remove "JOB " prefix if present
                clean = line.replace("JOB ", "").replace("Job ", "")

                parts = clean.split(":", 1)
                raw_id    = parts[0].strip()
                tech_stack = parts[1].strip() if len(parts) > 1 else ""

                # Only accept if the ID is a number
                try:
                    job_id = int(raw_id)
                    if tech_stack:
                        results[job_id] = tech_stack
                except ValueError:
                    continue  # skip lines that don't match format

            # Check if we got results for all jobs in batch
            batch_ids = [int(row[0]) for row in batch]
            missing   = [jid for jid in batch_ids if jid not in results]

            if missing:
                print(f"[Batch {batch_num}] Attempt {attempt} failed: "
                      f"Missing results for {len(missing)} jobs")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_WAIT)
                    continue

            # ── Save to database ─────────────────────────────────────
            for source_id, _ in batch:
                job_id = int(source_id)
                if job_id in results:
                    tech = results[job_id]
                    try:
                        cursor.execute(
                            "UPDATE jobs SET tech_stack = ? WHERE source_id = ?",
                            (tech, source_id)
                        )
                        print(f"Analyzed Job {source_id}: {tech}")
                    except Exception as e:
                        print(f"[ERROR] Failed to update job {source_id}: {e}")
                else:
                    # Even if missing, don't crash — just warn
                    print(f"[WARN] No tags found for job {source_id}, skipping")

            try:
                conn.commit()
            except Exception as e:
                print(f"[ERROR] Failed to commit batch {batch_num}: {e}")

            success = True
            break  # exit retry loop

        if not success:
            print(f"[Batch {batch_num}] All {MAX_RETRIES} retries failed. Skipping.")

    conn.close()

    # ── Final summary ────────────────────────────────────────────────
    elapsed      = (time.time() - start_time) * 1000
    total_tokens = total_input_tokens + total_output_tokens
    print(f"\nTotal tokens used: {total_tokens}, took {elapsed:.3f}ms")

    return total_input_tokens, total_output_tokens, elapsed


# ── Entry point ──────────────────────────────────────────────────────
if __name__ == "__main__":
    tag_data("data/jobsOllama.db")