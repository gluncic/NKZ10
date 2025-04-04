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
    """Pretvara tekst u 'slug' (mala slova, bez specijalnih znakova)."""
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

# Grupiranje podataka: rodovi[rod] = set(skupina), skupine[skupina] = list(zanimanja)
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

# Početna stranica – prikazuje rodove (collapsed)
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

# Expanded rod: prikazuje redak s rodom i ispod njega retke za skupine (collapsed)
@app.get("/skupine/{rod_slug}", response_class=HTMLResponse)
def expand_rod(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    skupine_lista = sorted(list(rodovi.get(rod, [])))
    # Prvi redak: rod (sa collapse kontrolom)
    html = f"""
    <tr class="rod-row" id="rod-{rod_slug}">
      <td>
        {rod}
        <span style="float:right; cursor:pointer;" 
              hx-get="/collapse-rod/{rod_slug}" 
              hx-target="#rod-{rod_slug}" 
              hx-swap="outerHTML">▲</span>
      </td>
    </tr>
    """
    # Dodajemo retke za svaku skupinu
    for skupina in skupine_lista:
        skupina_slug = slugify(skupina)
        html += f"""
        <tr class="group-row" id="group-{skupina_slug}">
          <td style="padding-left:20px;">
            {skupina}
            <span style="float:right; cursor:pointer;" 
                  hx-get="/expand-group/{skupina_slug}" 
                  hx-target="#group-{skupina_slug}" 
                  hx-swap="outerHTML">▼</span>
          </td>
        </tr>
        """
    return html

# Collapsed rod: vraća samo rodov redak (kao u početnom stanju)
@app.get("/collapse-rod/{rod_slug}", response_class=HTMLResponse)
def collapse_rod(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    return f"""
    <tr class="rod-row" id="rod-{rod_slug}">
      <td>
        <a class="rod-link" href="#" hx-get="/skupine/{rod_slug}" hx-target="#rod-{rod_slug}" hx-swap="outerHTML">{rod}</a>
      </td>
    </tr>
    """

# --- SKUPINE i ZANIMANJA ---

# Expanded group: prikazuje skupinu s collapse kontrolom i ispod retke za zanimanja (collapsed)
@app.get("/expand-group/{group_slug}", response_class=HTMLResponse)
def expand_group(request: Request, group_slug: str):
    group = get_skupina_by_slug(group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    lista_zanimanja = skupine.get(group, [])
    # Prvi redak: skupina (expanded) s collapse kontrolom
    html = f"""
    <tr class="group-row" id="group-{group_slug}">
      <td style="padding-left:20px;">
        {group}
        <span style="float:right; cursor:pointer;" 
              hx-get="/collapse-group/{group_slug}" 
              hx-target="#group-{group_slug}" 
              hx-swap="outerHTML">▲</span>
      </td>
    </tr>
    """
    # Dodaj retke za svako zanimanje
    for z in lista_zanimanja:
        sifra = z["sifra"]
        ime = z["ime"]
        html += f"""
        <tr class="occupation-row" id="occ-{sifra}">
          <td style="padding-left:40px;">
            <a class="zanimanje-link" href="#" hx-get="/toggle/{sifra}" hx-target="#occ-{sifra}" hx-swap="outerHTML">
              {ime}
            </a>
          </td>
        </tr>
        """
    return html

# Collapsed group: vraća samo skupinski redak s collapsed stilom
@app.get("/collapse-group/{group_slug}", response_class=HTMLResponse)
def collapse_group(request: Request, group_slug: str):
    group = get_skupina_by_slug(group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    return f"""
    <tr class="group-row" id="group-{group_slug}">
      <td style="padding-left:20px;">
        <a class="skupina-link" href="#" hx-get="/expand-group/{group_slug}" hx-target="#group-{group_slug}" hx-swap="outerHTML">
          {group}
        </a>
      </td>
    </tr>
    """

# --- ZANIMANJA OPIS ---

# Toggle – expanded occupation: prikazuje opis zanimanja
@app.get("/toggle/{code}", response_class=HTMLResponse)
def toggle_opis(request: Request, code: str):
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    opis = zan_dict[code]["description"]
    ime = zan_dict[code]["ime"]
    return f"""
    <tr class="occupation-row" id="occ-{code}">
      <td style="padding-left:40px;">
        <a class="zanimanje-link" href="#" hx-get="/hide/{code}" hx-target="#occ-{code}" hx-swap="outerHTML">
          {ime}
        </a>
        <div class="opis">{opis}</div>
      </td>
    </tr>
    """

# Toggle – collapsed occupation: prikazuje samo naziv zanimanja
@app.get("/hide/{code}", response_class=HTMLResponse)
def hide_opis(request: Request, code: str):
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    ime = zan_dict[code]["ime"]
    return f"""
    <tr class="occupation-row" id="occ-{code}">
      <td style="padding-left:40px;">
        <a class="zanimanje-link" href="#" hx-get="/toggle/{code}" hx-target="#occ-{code}" hx-swap="outerHTML">
          {ime}
        </a>
      </td>
    </tr>
    """

@app.get("/test", response_class=HTMLResponse)
def test(request: Request):
    return "<tr><td>Test uspješan!</td></tr>"
