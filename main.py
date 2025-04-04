import re
import unicodedata
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def slugify(value: str) -> str:
    """
    Normalizira tekst, uklanja dijakritike, nealfanumeričke znakove i zamjenjuje razmake s crticama.
    Vraća niz s malim slovima.
    """
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[-\s]+", "-", value)
    return value

def get_rod_by_slug(slug: str) -> str:
    for rod in rodovi:
        if slugify(rod) == slug:
            return rod
    return None

def get_skupina_by_slug(slug: str) -> str:
    for skupina in skupine:
        if slugify(skupina) == slug:
            return skupina
    return None

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
    # Za svaki rod spremamo originalnu vrijednost, slug i popis skupina (koji se samo prosljeđuje predlošku)
    rods = []
    for rod, skupina_set in rodovi.items():
        rods.append({
            "rod": rod,
            "slug": slugify(rod),
            "skupine": sorted(list(skupina_set))
        })
    rods.sort(key=lambda x: x["rod"])
    return templates.TemplateResponse("index.html", {"request": request, "rods": rods})

@app.get("/skupine/{rod_slug}", response_class=HTMLResponse)
def skupine_rod(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    skupine_lista = sorted(list(rodovi.get(rod, [])))
    html = f"<div class='blok rod-container' id='rod-{rod_slug}'>"
    # Link za rod (prva razina)
    html += f'<a class="rod-link" href="#" hx-get="/sakrij-rod/{rod_slug}" hx-target="#rod-{rod_slug}" hx-swap="outerHTML">{rod}</a>'
    html += "<ul>"
    for skupina in skupine_lista:
        skupina_slug = slugify(skupina)
        # Omotavamo link za skupinu u div sa specifičnom klasom
        html += f'<li><div id="skupina-{skupina_slug}" class="skupina-container">'
        html += f'<a class="skupina-link" href="#" hx-get="/zanimanja/{skupina_slug}" hx-target="#skupina-{skupina_slug}" hx-swap="outerHTML">{skupina}</a>'
        html += "</div></li>"
    html += "</ul></div>"
    return html

@app.get("/sakrij-rod/{rod_slug}", response_class=HTMLResponse)
def sakrij_rod(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    html = f"<div class='blok rod-container' id='rod-{rod_slug}'>"
    html += f'<a class="rod-link" href="#" hx-get="/skupine/{rod_slug}" hx-target="#rod-{rod_slug}" hx-swap="outerHTML">{rod}</a>'
    html += "</div>"
    return html

@app.get("/zanimanja/{skupina_slug}", response_class=HTMLResponse)
def zanimanja_skupina(request: Request, skupina_slug: str):
    skupina = get_skupina_by_slug(skupina_slug)
    if not skupina:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    zanimanja = skupine.get(skupina, [])
    html = f"<div class='blok skupina-container' id='skupina-{skupina_slug}'>"
    # Link za skupinu (druga razina)
    html += f'<a class="skupina-link" href="#" hx-get="/sakrij-skupinu/{skupina_slug}" hx-target="#skupina-{skupina_slug}" hx-swap="outerHTML">{skupina}</a>'
    html += "<ul>"
    for z in zanimanja:
        sifra = z["sifra"]
        ime = z["ime"]
        # Omotavamo link zanimanja u div sa specifičnom klasom
        html += f'<li><div id="blok-{sifra}" class="zanimanje-container">'
        html += f'<a class="zanimanje-link" href="#" hx-get="/toggle/{sifra}" hx-target="#blok-{sifra}" hx-swap="outerHTML">{ime}</a>'
        html += "</div></li>"
    html += "</ul></div>"
    return html

@app.get("/sakrij-skupinu/{skupina_slug}", response_class=HTMLResponse)
def sakrij_skupinu(request: Request, skupina_slug: str):
    skupina = get_skupina_by_slug(skupina_slug)
    if not skupina:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    html = f"<div class='blok skupina-container' id='skupina-{skupina_slug}'>"
    html += f'<a class="skupina-link" href="#" hx-get="/zanimanja/{skupina_slug}" hx-target="#skupina-{skupina_slug}" hx-swap="outerHTML">{skupina}</a>'
    html += "</div>"
    return html

@app.get("/toggle/{code}", response_class=HTMLResponse)
def toggle_opis(request: Request, code: str):
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    opis = zan_dict[code]["description"]
    ime = zan_dict[code]["ime"]
    html = f"<div class='zanimanje-blok zanimanje-container' id='blok-{code}'>"
    html += f'<a class="zanimanje-link" href="#" hx-get="/sakrij/{code}" hx-target="#blok-{code}" hx-swap="outerHTML">{ime}</a>'
    html += f"<div class='opis'>{opis}</div></div>"
    return html

@app.get("/sakrij/{code}", response_class=HTMLResponse)
def sakrij_opis(request: Request, code: str):
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    ime = zan_dict[code]["ime"]
    html = f"<div class='zanimanje-blok zanimanje-container' id='blok-{code}'>"
    html += f'<a class="zanimanje-link" href="#" hx-get="/toggle/{code}" hx-target="#blok-{code}" hx-swap="outerHTML">{ime}</a>'
    html += "</div>"
    return html

@app.get("/test", response_class=HTMLResponse)
def test(request: Request):
    return "<div id='output'>Test uspješan!</div>"
