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
    Pretvara tekst u 'slug' – mala slova, bez dijakritika i specijalnih znakova,
    a razmaci se zamjenjuju crticama.
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

# Učitavanje podataka iz JSON-a
with open("NKZ_descriptions_chatGPT4omini.json", encoding="utf-8") as f:
    zan_dict = json.load(f)

# Grupiranje podataka:
# - rodovi[rod] = set(skupina1, skupina2, …)
# - skupine[skupina] = [ { "sifra": ..., "ime": ... }, ... ]
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

# Početna stranica: prikazuje rodove u collapsed stanju – kao pojedinačne redove u tablici
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

# Expanded rod – vraća redak za rod (s collapse kontrolom) i odmah ispod njega retke za skupine (u collapsed stanju)
@app.get("/expand-rod/{rod_slug}", response_class=HTMLResponse)
def expand_rod(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    groups = sorted(list(rodovi.get(rod, [])))
    html = f'<tr id="rod-{rod_slug}" class="rod-row"><td><span class="rod-text">{rod}</span> <a class="rod-link" href="#" hx-get="/collapse-rod/{rod_slug}" hx-target="#rod-{rod_slug}" hx-swap="outerHTML">(Collapse)</a></td></tr>'
    for group in groups:
        group_slug = slugify(group)
        # Group row – indent od 20px
        html += f'<tr id="group-{group_slug}" class="group-row"><td style="padding-left:20px;"><a class="skupina-link" href="#" hx-get="/expand-group/{group_slug}" hx-target="#group-{group_slug}" hx-swap="outerHTML">{group}</a></td></tr>'
    return html

# Collapsed rod – vraća samo rodov redak u collapsed stilu (kao na početku)
@app.get("/collapse-rod/{rod_slug}", response_class=HTMLResponse)
def collapse_rod(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    return f'<tr id="rod-{rod_slug}" class="rod-row"><td><a class="rod-link" href="#" hx-get="/expand-rod/{rod_slug}" hx-target="#rod-{rod_slug}" hx-swap="outerHTML">{rod}</a></td></tr>'

# --- SKUPINE i ZANIMANJA ---

# Expanded group – vraća group redak (s collapse kontrolom) i retke za svako zanimanje (collapsed)
@app.get("/expand-group/{group_slug}", response_class=HTMLResponse)
def expand_group(request: Request, group_slug: str):
    group = get_skupina_by_slug(group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    occs = skupine.get(group, [])
    html = f'<tr id="group-{group_slug}" class="group-row"><td style="padding-left:20px;"><span class="group-text">{group}</span> <a class="skupina-link" href="#" hx-get="/collapse-group/{group_slug}" hx-target="#group-{group_slug}" hx-swap="outerHTML">(Collapse)</a></td></tr>'
    for occ in occs:
        code = occ["sifra"]
        name = occ["ime"]
        # Occupation row – indent od 20px (kao i skupina)
        html += f'<tr id="occ-{code}" class="occupation-row"><td style="padding-left:20px;"><a class="zanimanje-link" href="#" hx-get="/toggle/{code}" hx-target="#occ-{code}" hx-swap="outerHTML">{name}</a></td></tr>'
    return html

# Collapsed group – vraća samo group redak u collapsed stilu
@app.get("/collapse-group/{group_slug}", response_class=HTMLResponse)
def collapse_group(request: Request, group_slug: str):
    group = get_skupina_by_slug(group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    return f'<tr id="group-{group_slug}" class="group-row"><td style="padding-left:20px;"><a class="skupina-link" href="#" hx-get="/expand-group/{group_slug}" hx-target="#group-{group_slug}" hx-swap="outerHTML">{group}</a></td></tr>'

# Toggle za zanimanje – expanded state (prikazuje opis) i collapsed state
@app.get("/toggle/{code}", response_class=HTMLResponse)
def toggle_opis(request: Request, code: str):
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    opis = zan_dict[code]["description"]
    name = zan_dict[code]["ime"]
    # Expanded occupation – naziv ostaje s indentom (20px)
    return f'<tr id="occ-{code}" class="occupation-row"><td style="padding-left:20px;"><span class="occupation-text">{name}</span> <a class="zanimanje-link" href="#" hx-get="/hide/{code}" hx-target="#occ-{code}" hx-swap="outerHTML">(Hide)</a><div class="opis">{opis}</div></td></tr>'

@app.get("/hide/{code}", response_class=HTMLResponse)
def hide_opis(request: Request, code: str):
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    name = zan_dict[code]["ime"]
    return f'<tr id="occ-{code}" class="occupation-row"><td style="padding-left:20px;"><a class="zanimanje-link" href="#" hx-get="/toggle/{code}" hx-target="#occ-{code}" hx-swap="outerHTML">{name}</a></td></tr>'

@app.get("/test", response_class=HTMLResponse)
def test(request: Request):
    return "<tr><td>Test uspješan!</td></tr>"
