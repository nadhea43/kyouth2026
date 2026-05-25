from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI() # [cite: 24]

# Point Jinja2 to your templates directory
templates = Jinja2Templates(directory="src/templates") 

@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    # Renders the HTML file when someone visits http://localhost:8000
    return templates.TemplateResponse(request=request, name="chat_page.html")