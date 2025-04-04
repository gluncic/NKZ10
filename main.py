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

@app.get("/toggle/{code}", response_class=HTMLResponse)
def toggle_opis(request: Request, code: str):
    opis = zan_dict[code]["description"]
    ime = zan_dict[code]["ime"]

    return f"""
    <div id="blok-{code}" class="zanimanje-blok">
        <div class="zanimanje"
             hx-get="/sakrij/{code}"
             hx-target="#blok-{code}"
             hx-swap="outerHTML"
             hx-trigger="click">
            {ime}
        </div>
        <div id="opis-{code}" class="opis">{opis}</div>
    </div>
    """

@app.get("/sakrij/{code}", response_class=HTMLResponse)
def sakrij_opis(request: Request, code: str):
    ime = zan_dict[code]["ime"]
    return f"""
    <div id="blok-{code}" class="zanimanje-blok">
        <div class="zanimanje"
             hx-get="/toggle/{code}"
             hx-target="#blok-{code}"
             hx-swap="outerHTML"
             hx-trigger="click">
            {ime}
        </div>
    </div>
    """
