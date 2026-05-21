import sqlite3
import time
import os
import re
import json
from pathlib import Path
from typing import List, Tuple
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai

# load .env file for API keys
BASE_DIR = Path(__file__).parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# config Gemini
GEMINI_MODEL = "gemini-2.5-flash"
MAX_RETRIES = 3
RETRY_WAIT = 5  # seconds

# Pydantic model
class SkillGapResult(BaseModel):
    gaps : List[str]
    tokens : int = 0
    time : int = 0

# to remove common prompt injection attempts before sending to AI 
def sanitize_input(text: str) -> str:
    # remove lines that look like prompt injection attempts
    injection_patterns = [
        r"ignore\s+(all\s+)?(previous\s+|above\s+)?instructions?",
        r"you\s+are\s+now",
        r"act\s+as\s+(if\s+)?",
        r"pretend\s+(you\s+are|to\s+be)",
        r"forget\s+(all\s+)?previous",
        r"disregard\s+(all\s+)?",
        r"do\s+not\s+follow",
        r"system\s*prompt",
        r"jailbreak",
        r"<\s*script",           # HTML/script injection
        r"prompt\s*injection"
    ]
    
    lines = text.splitlines()
    clean_lines = []
    for line in lines:
        if re.search(pattern, line, re.IGNORECASE):
            print(f"[Sanitize] Removing suspicious line: {line.strip()}")
            is_injection = True
            break
        if not is_injection:
            clean_lines.append(line)
    return "\n".join(clean_lines)
    
# Extracts skills from resume using gemini AI
def extract_resume_skills(client, resume_text: str) -> tuple[set, int]:
    prompt = """You are a technical skill extractor analyzing a resume.
    Extract ONLY the technical skills, tools, programming languages, and frameworks 
    from the resume below.

    Rules:
    - Output ONLY a JSON array of strings, nothing else
    - Lowercase everything
    - Do NOT include: soft skills, languages (English/Malay), certifications, hobbies
    - Keep compound names intact: "c++" not "c", "node.js" not "node"
    - Do NOT add skills not mentioned in the resume

    Example output format:
    ["python", "sql", "docker", "aws", "react"]

    Resume:
    \"\"\"
    {resume}
    \"\"\"

    Reply with ONLY the JSON array. No explanation, no markdown, no extra text.

""".format(resume=resume_text)
    
    total_tokens = 0

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            reply = response.text.strip()

            #count tokens
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                total_tokens += (response.usage_metadata.prompt_token_count or 0)
            else:
                total_tokens += len(prompt.split())  # fallback token estimation
        
            # clean reply 
            reply = re.sub(r"```(?:json)?", "", reply).strip()  # remove markdown code fences if present
            reply = reply.strip("`").strip()

            # parse JSON array
            skills_list = json.loads(reply)

            # validate that it's a list of strings
            if not isinstance(skills_list, list):
                print(f"[Error] Expected a JSON array but got: {reply}")
                continue

            # clean each skill: lowercase, strip whitespace
            skills_set = set(s.strip().lower() for s in skills_list if isinstance(s, str))
            return skills_set, total_tokens
        
        except Exception as e:
            print(f"[Attempt {attempt}] Error extracting skills: {e}")
            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_WAIT}s...")
            time.sleep(RETRY_WAIT)

    # If all retries fail, return empty set and total tokens counted    
    print("Failed to extract skills after multiple attempts.")
    return set(), total_tokens

# get all unique skills from jobs db
def get_market_skills(db_url: str) -> set:
    market_skills = set()

    try:
        conn = sqlite3.connect(db_url)
        cursor = conn.cursor()

        cursor.execute("""
                SELECT tech_stack FROM jobs
                WHERE tech_stack IS NOT NULL
            """ )
        rows = cursor.fetchall()
        conn.close()

        for (tech_stack,) in rows:
            # split tech_stack by comma and strip whitespace
            skills = [s.strip().lower() for s in tech_stack.split(",") if s.strip()]
            market_skills.update(skills)
            
    except Exception as e:
        print(f"[ERROR] Cannot read from database: {e}")

    return market_skills

# handle cases like "c/c++" vs "c++" vs "c"
def normalize_skill(skill:str) -> set:
    variants = {skill}

    #handle slash-separated cam skills like "c/c++" or "node.js/react"
    if "/" in skill:
        parts = skill.split("/")
        for part in parts:
            variants.add(part.strip())

    return variants

def build_normalized_set(skills: set) -> dict:
    lookup = {}
    for skill in skills:
        for variant in normalize_skill(skill):
             lookup[variant] = skill
    return lookup

# main function to find skill gaps
def find_skill_gaps(input_file_path:str , db_url:str) -> SkillGapResult:
    start_time = time.time()

    # setup Gemini
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not found in environment variables.")
        return SkillGapResult(gaps=[], tokens=0, time=0)
    
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"[ERROR] Failed to initialize Gemini client: {e}")
        return SkillGapResult(gaps=[], tokens=0, time=0)
    
    # read resume text from file
    try:
        resume_text = Path(input_file_path).read_text(encoding="utf-8")
    except Exception as e:
        print(f"[ERROR] Failed to read resume file: {e}")
        return SkillGapResult(gaps=[], tokens=0, time=0)
    
    # sanitize resume text to remove potential prompt injections
    resume_text = sanitize_input(resume_text)

    # extract skills from resume
    print("Extracting skills from resume...")
    resume_skills, tokens_used = extract_resume_skills(client, resume_text)
    print(f"Resume skills found: {sorted(resume_skills)} \n")

    # get market skills from database
    print("Reading market skills from database...")
    market_skills = get_market_skills(db_url)
    print(f"UniqueMarket skills found: {len(market_skills)}\n {sorted(market_skills)} \n")

    # build normalized lookup for resume skills
    #This handles "c/c++" matching against "c" or "c++" in market
    resume_lookup = build_normalized_set(resume_skills)

    # find skill gaps
    gaps = []
    for market_skill in market_skills:
        # check if this market skill or any of its variants is in the resume skills
        market_variants = normalize_skill(market_skill)
        covered = any(variant in resume_lookup for variant in market_variants)
        if not covered:
            gaps.append(market_skill)

    # sort alpabetically and lowercase
    gaps = sorted(set(gaps))

    # calculate time taken  
    elapsed_time = int(time.time() - start_time) * 1000  # convert to milliseconds

    result = SkillGapResult(
        gaps=gaps,
        tokens=tokens_used, 
        time=elapsed_time
        )
    
    print(f"gaps found : {result.gaps} ")
    print(f"time taken : {elapsed_time} ms  tokens : {tokens_used} ")

    return result

if __name__ == "__main__":
    input_file = "data/resume_d3.txt"
    db_url = "data/jobs.db"

    find_skill_gaps(input_file, db_url)
      

    
        