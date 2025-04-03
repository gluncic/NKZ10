# main.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Učitavanje zanimanja s opisima
with open("NKZ_descriptions_chatGPT4omini.json", encoding="utf-8") as f:
    zan_dict = json.load(f)

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "zanimanja": zan_dict})

@app.get("/opis/{code}", response_class=HTMLResponse)
def get_opis(request: Request, code: str):
    opis = zan_dict[code]["description"]
    return f"""
        <div id='opis-{code}' class='opis' 
             hx-get='/sakrij/{code}' 
             hx-trigger='click' 
             hx-swap='outerHTML'>
            {opis}
        </div>
    """

@app.get("/sakrij/{code}", response_class=HTMLResponse)
def sakrij_opis(request: Request, code: str):
    return f"<div id='opis-{code}'></div>"
