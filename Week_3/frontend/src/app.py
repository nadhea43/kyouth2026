import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

load_dotenv()

app = FastAPI() # [cite: 24]

# Point Jinja2 to your templates directory
templates = Jinja2Templates(directory="src/templates") 

# 1. The Route for your new Landing Page
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="landing_page.html", 
        context={}
        
    )

# 2. The Route for your Chat Page
@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8001")
    return templates.TemplateResponse(
        request=request, 
        name="chat_page.html", 
        context={"backend_url": backend_url}
    )

