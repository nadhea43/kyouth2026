from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import tempfile

from week_2.prompt_model import prompt_model
from week_2.find_skill_gaps import find_skill_gaps

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

# Path to jobs database — sits in src/week_2/
DB_PATH = os.path.join(os.path.dirname(__file__), "week_2", "jobs_d3_eval.db")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    pdf_text: str = ""

# Keywords that trigger skill gap analysis
SKILL_GAP_KEYWORDS = [
    "find skills gap",
    "skill gap",
    "skills gap",
    "find skill gap",
    "skill gaps",
    "skills gaps",
]

def is_skill_gap_request(message: str) -> bool:
    """Check if user is asking for skill gap analysis"""
    return any(keyword in message.lower() for keyword in SKILL_GAP_KEYWORDS)

@app.post("/chat")
def chat(request: ChatRequest):

    # ── Route 1: Skill gap analysis ───────────────────────────
    # Triggered when user says "find skills gap" AND has uploaded a PDF
    if is_skill_gap_request(request.message):

        # Must have a PDF attached
        if not request.pdf_text:
            return JSONResponse(content={
                "reply": "Please upload your resume PDF first, then ask me to find skill gaps!"
            })

        # Write the PDF text to a temp file — find_skill_gaps() needs a file path
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(request.pdf_text)
            tmp_path = tmp.name

        try:
            # Call your Week 2 function!
            result = find_skill_gaps(tmp_path, DB_PATH)

            if result.gaps:
                gaps_str = " - " + "\n - ".join(result.gaps)
                reply = f"Skills gap identified:\n{gaps_str}"
            else:
                reply = "No skill gaps found — your resume covers all the skills in our database!"

        except Exception as e:
            reply = f"Error during skill gap analysis: {str(e)}"

        finally:
            # Clean up temp file
            os.unlink(tmp_path)

        return JSONResponse(content={"reply": reply})

    # ── Route 2: Normal chat (with or without PDF) ────────────
    else:
        if request.pdf_text:
            prompt = f"""The user has provided this document:
{request.pdf_text}

User's question: {request.message}"""
        else:
            prompt = request.message

        reply = prompt_model(GEMINI_MODEL, prompt)
        return JSONResponse(content={"reply": reply})