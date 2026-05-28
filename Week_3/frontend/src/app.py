import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

load_dotenv()

app = FastAPI() # [cite: 24]

# Point Jinja2 to your templates directory
templates = Jinja2Templates(directory="src/templates") 

@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8001")
    return templates.TemplateResponse(
        request=request,                    # ← pass as keyword argument
        name="chat_page.html",              # ← name as keyword argument
        context={"backend_url": backend_url} # ← context WITHOUT request inside
    )