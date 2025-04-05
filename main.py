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
    # Normaliziramo tekst, uklanjamo dijakritike, pretvaramo u ASCII, mala slova i zamjenjujemo razmake s "-"
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

# Grupiranje podataka: rodovi[rod] = set(skupina), skupine[skupina] = [ { "sifra":..., "ime":... }, ... ]
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
    rods = []
    for rod, skupina_set in rodovi.items():
        rods.append({
            "rod": rod,
            "slug": slugify(rod),
            "skupine": sorted(list(skupina_set))
        })
    rods.sort(key=lambda x: x["rod"])
    return templates.TemplateResponse("index.html", {"request": request, "rods": rods})

# --- RODOVI ---

# Expanded rod – vraća sadržaj koji uključuje rod i ispod njega retke za skupine.
@app.get("/expand-rod/{rod_slug}", response_class=HTMLResponse)
def expand_rod(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    groups = sorted(list(rodovi.get(rod, [])))
    html = f"<div class='blok' id='rod-{rod_slug}'>"
    # Rod ostaje isti (bez promjene stila), samo se ispod dodaju skupine.
    html += f'<a class="rod-link" href="#" hx-get="/collapse-rod/{rod_slug}" hx-target="#rod-{rod_slug}" hx-swap="outerHTML">{rod}</a>'
    html += "<ul>"
    for group in groups:
        group_slug = slugify(group)
        html += f"<li><div class='blok' id='skupina-{group_slug}'>"
        html += f'<a class="skupina-link" href="#" hx-get="/expand-group/{group_slug}" hx-target="#skupina-{group_slug}" hx-swap="outerHTML">{group}</a>'
        html += "</div></li>"
    html += "</ul></div>"
    return html

# Collapsed rod – vraća isto kao što je učitano u index.html
@app.get("/collapse-rod/{rod_slug}", response_class=HTMLResponse)
def collapse_rod(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    # Vraćamo početni HTML za rod (bez podataka o skupinama)
    return f"<div class='blok' id='rod-{rod_slug}'><a class='rod-link' href='#' hx-get='/expand-rod/{rod_slug}' hx-target='#rod-{rod_slug}' hx-swap='outerHTML'>{rod}</a></div>"

# --- SKUPINE i ZANIMANJA ---

# Expanded group – prikazuje skupinu i ispod nje listu zanimanja.
@app.get("/expand-group/{group_slug}", response_class=HTMLResponse)
def expand_group(request: Request, group_slug: str):
    group = get_skupina_by_slug(group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    occs = skupine.get(group, [])
    html = f"<div class='blok' id='skupina-{group_slug}' style='margin-left:20px;'>"
    html += f'<a class="skupina-link" href="#" hx-get="/collapse-group/{group_slug}" hx-target="#skupina-{group_slug}" hx-swap="outerHTML">{group}</a>'
    html += "<ul>"
    for occ in occs:
        code = occ["sifra"]
        name = occ["ime"]
        html += f"<li><div class='blok' id='blok-{code}' style='margin-left:20px;'>"
        html += f'<a class="zanimanje-link" href="#" hx-get="/toggle/{code}" hx-target="#blok-{code}" hx-swap="outerHTML">{name}</a>'
        html += "</div></li>"
    html += "</ul></div>"
    return html

# Collapsed group – vraća početni HTML za skupinu (kao u index.html)
@app.get("/collapse-group/{group_slug}", response_class=HTMLResponse)
def collapse_group(request: Request, group_slug: str):
    group = get_skupina_by_slug(group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    return f"<div class='blok' id='skupina-{group_slug}' style='margin-left:20px;'><a class='skupina-link' href='#' hx-get='/expand-group/{group_slug}' hx-target='#skupina-{group_slug}' hx-swap='outerHTML'>{group}</a></div>"

# Toggle za zanimanje – expanded state: opis je prikazan; collapsed state: samo naziv.
@app.get("/toggle/{code}", response_class=HTMLResponse)
def toggle_opis(request: Request, code: str):
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    opis = zan_dict[code]["description"]
    name = zan_dict[code]["ime"]
    # Expanded state: naziv ostaje u istom stilu i indentu
    return f"<div class='blok' id='blok-{code}' style='margin-left:20px;'><a class='zanimanje-link' href='#' hx-get='/hide/{code}' hx-target='#blok-{code}' hx-swap='outerHTML'>{name}</a><div class='opis'>{opis}</div></div>"

@app.get("/hide/{code}", response_class=HTMLResponse)
def hide_opis(request: Request, code: str):
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    name = zan_dict[code]["ime"]
    return f"<div class='blok' id='blok-{code}' style='margin-left:20px;'><a class='zanimanje-link' href='#' hx-get='/toggle/{code}' hx-target='#blok-{code}' hx-swap='outerHTML'>{name}</a></div>"

@app.get("/test", response_class=HTMLResponse)
def test(request: Request):
    return "<div id='output'>Test uspješan!</div>"
