from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
from urllib.parse import quote, unquote
#6
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Učitavanje podataka iz JSON datoteke
with open("NKZ_descriptions_chatGPT4omini.json", encoding="utf-8") as f:
    zan_dict = json.load(f)

# Grupiranje podataka: mapiramo rod na skupine, a skupina na zanimanja
rodovi = {}
skupine = {}

for sifra, data in zan_dict.items():
    rod = data["rod"]
    skupina = data["skupina"]
    rodovi.setdefault(rod, set()).add(skupina)
    skupine.setdefault(skupina, []).append({
        "sifra": sifra,
        "ime": data["ime"]
    })

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # Za svaki rod spremamo originalnu i URL-enkodiranu vrijednost
    rods = []
    for rod, skupina_set in rodovi.items():
        rods.append({
            "rod": rod,
            "encoded": quote(rod),
            "skupine": sorted(list(skupina_set))
        })
    rods.sort(key=lambda x: x["rod"])
    return templates.TemplateResponse("index.html", {"request": request, "rods": rods})

@app.get("/skupine/{rod}", response_class=HTMLResponse)
def skupine_rod(request: Request, rod: str):
    rod = unquote(rod)
    rod_enc = quote(rod)
    skupine_lista = sorted(list(rodovi.get(rod, [])))
    html = f"<div class='blok' id='rod-{rod_enc}'>"
    html += f'<a href="#" hx-get="/sakrij-rod/{rod_enc}" hx-target="#rod-{rod_enc}" hx-swap="outerHTML">{rod}</a>'
    html += "<ul>"
    for skupina in skupine_lista:
        skupina_enc = quote(skupina)
        html += f'<li><a href="#" hx-get="/zanimanja/{skupina_enc}" hx-target="#skupina-{skupina_enc}" hx-swap="outerHTML">{skupina}</a></li>'
    html += "</ul></div>"
    return html

@app.get("/sakrij-rod/{rod}", response_class=HTMLResponse)
def sakrij_rod(request: Request, rod: str):
    rod = unquote(rod)
    rod_enc = quote(rod)
    html = f"<div class='blok' id='rod-{rod_enc}'>"
    html += f'<a href="#" hx-get="/skupine/{rod_enc}" hx-target="#rod-{rod_enc}" hx-swap="outerHTML">{rod}</a>'
    html += "</div>"
    return html

@app.get("/zanimanja/{skupina}", response_class=HTMLResponse)
def zanimanja_skupina(request: Request, skupina: str):
    skupina = unquote(skupina)
    skupina_enc = quote(skupina)
    zanimanja = skupine.get(skupina, [])
    html = f"<div class='blok' id='skupina-{skupina_enc}'>"
    html += f'<a href="#" hx-get="/sakrij-skupinu/{skupina_enc}" hx-target="#skupina-{skupina_enc}" hx-swap="outerHTML">{skupina}</a>'
    html += "<ul>"
    for z in zanimanja:
        sifra = z["sifra"]
        ime = z["ime"]
        html += f'<li><a href="#" hx-get="/toggle/{sifra}" hx-target="#blok-{sifra}" hx-swap="outerHTML">{ime}</a></li>'
    html += "</ul></div>"
    return html

@app.get("/sakrij-skupinu/{skupina}", response_class=HTMLResponse)
def sakrij_skupinu(request: Request, skupina: str):
    skupina = unquote(skupina)
    skupina_enc = quote(skupina)
    html = f"<div class='blok' id='skupina-{skupina_enc}'>"
    html += f'<a href="#" hx-get="/zanimanja/{skupina_enc}" hx-target="#skupina-{skupina_enc}" hx-swap="outerHTML">{skupina}</a>'
    html += "</div>"
    return html

@app.get("/toggle/{code}", response_class=HTMLResponse)
def toggle_opis(request: Request, code: str):
    opis = zan_dict[code]["description"]
    ime = zan_dict[code]["ime"]
    html = f"<div class='zanimanje-blok' id='blok-{code}'>"
    html += f'<a href="#" hx-get="/sakrij/{code}" hx-target="#blok-{code}" hx-swap="outerHTML">{ime}</a>'
    html += f"<div class='opis'>{opis}</div></div>"
    return html

@app.get("/sakrij/{code}", response_class=HTMLResponse)
def sakrij_opis(request: Request, code: str):
    ime = zan_dict[code]["ime"]
    html = f"<div class='zanimanje-blok' id='blok-{code}'>"
    html += f'<a href="#" hx-get="/toggle/{code}" hx-target="#blok-{code}" hx-swap="outerHTML">{ime}</a>'
    html += "</div>"
    return html

@app.get("/test", response_class=HTMLResponse)
def test(request: Request):
    return "<div id='output'>Test uspješan!</div>"
