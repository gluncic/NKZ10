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
    """Pretvara tekst u slug: mala slova, bez specijalnih znakova."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "-", value)

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

# Grupiranje podataka
# rodovi[rod] = set(skupina, ...)
# skupine[skupina] = [ { "sifra": ..., "ime": ... }, ... ]
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

# Početna stranica – prikazuje sve rodove u collapsed stanju
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

# Collapsed rod: samo redak s rod imenom i linkom za expand
@app.get("/collapse-rod/{rod_slug}", response_class=HTMLResponse)
def collapse_rod(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    return f'''
    <tr id="rod-{rod_slug}" class="rod-row">
      <td>
        <a class="rod-link" href="#" hx-get="/expand-rod/{rod_slug}" hx-target="#rod-{rod_slug}" hx-swap="outerHTML">{rod}</a>
      </td>
    </tr>
    '''

# Expanded rod: redak s rodom (s collapse kontrolom) i ispod njega redci za svaku skupinu (u collapsed stanju)
@app.get("/expand-rod/{rod_slug}", response_class=HTMLResponse)
def expand_rod(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    groups = sorted(list(rodovi.get(rod, [])))
    html = f'''
    <tr id="rod-{rod_slug}" class="rod-row">
      <td>
        {rod} <a class="rod-link" href="#" hx-get="/collapse-rod/{rod_slug}" hx-target="#rod-{rod_slug}" hx-swap="outerHTML">(Collapse)</a>
      </td>
    </tr>
    '''
    for group in groups:
        group_slug = slugify(group)
        html += f'''
        <tr id="group-{group_slug}" class="group-row">
          <td style="padding-left:20px;">
            <a class="skupina-link" href="#" hx-get="/collapse-group/{group_slug}" hx-target="#group-{group_slug}" hx-swap="outerHTML">{group}</a>
          </td>
        </tr>
        '''
    return html

# --- SKUPINE ---

# Collapsed group: prikazuje samo naziv skupine i link za expand
@app.get("/collapse-group/{group_slug}", response_class=HTMLResponse)
def collapse_group(request: Request, group_slug: str):
    group = get_skupina_by_slug(group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    return f'''
    <tr id="group-{group_slug}" class="group-row">
      <td style="padding-left:20px;">
        <a class="skupina-link" href="#" hx-get="/expand-group/{group_slug}" hx-target="#group-{group_slug}" hx-swap="outerHTML">{group}</a>
      </td>
    </tr>
    '''

# Expanded group: redak s nazivom skupine (s collapse kontrolom) i ispod njega redci za zanimanja (collapsed)
@app.get("/expand-group/{group_slug}", response_class=HTMLResponse)
def expand_group(request: Request, group_slug: str):
    group = get_skupina_by_slug(group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    occs = skupine.get(group, [])
    html = f'''
    <tr id="group-{group_slug}" class="group-row">
      <td style="padding-left:20px;">
        {group} <a class="skupina-link" href="#" hx-get="/collapse-group/{group_slug}" hx-target="#group-{group_slug}" hx-swap="outerHTML">(Collapse)</a>
      </td>
    </tr>
    '''
    for occ in occs:
        code = occ["sifra"]
        name = occ["ime"]
        html += f'''
        <tr id="occ-{code}" class="occupation-row">
          <td style="padding-left:20px;">
            <a class="zanimanje-link" href="#" hx-get="/toggle/{code}" hx-target="#occ-{code}" hx-swap="outerHTML">{name}</a>
          </td>
        </tr>
        '''
    return html

# --- ZANIMANJA OPIS ---

# Toggle – Expanded occupation: prikazuje opis zanimanja; collapsed occupation: samo naziv
@app.get("/toggle/{code}", response_class=HTMLResponse)
def toggle_opis(request: Request, code: str):
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    opis = zan_dict[code]["description"]
    name = zan_dict[code]["ime"]
    return f'''
    <tr id="occ-{code}" class="occupation-row">
      <td style="padding-left:20px;">
        <a class="zanimanje-link" href="#" hx-get="/hide/{code}" hx-target="#occ-{code}" hx-swap="outerHTML">{name}</a>
        <div class="opis">{opis}</div>
      </td>
    </tr>
    '''

@app.get("/hide/{code}", response_class=HTMLResponse)
def hide_opis(request: Request, code: str):
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    name = zan_dict[code]["ime"]
    return f'''
    <tr id="occ-{code}" class="occupation-row">
      <td style="padding-left:20px;">
        <a class="zanimanje-link" href="#" hx-get="/toggle/{code}" hx-target="#occ-{code}" hx-swap="outerHTML">{name}</a>
      </td>
    </tr>
    '''

@app.get("/test", response_class=HTMLResponse)
def test(request: Request):
    return "<tr><td>Test uspješan!</td></tr>"
