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
    """Pretvara tekst u 'slug' (samo mala slova, bez specijalnih znakova)."""
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

# rodovi[rod] = set(skupina)
rodovi = {}
# skupine[skupina] = [ { "sifra": ..., "ime": ... }, ... ]
skupine = {}

for sifra, data in zan_dict.items():
    rod = data["rod"]
    skupina = data["skupina"]
    rodovi.setdefault(rod, set()).add(skupina)
    skupine.setdefault(skupina, []).append({
        "sifra": sifra,
        "ime": data["ime"]
    })

# Početna stranica – prikazuje rodove u sakupljenom stanju (collapsed)
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

# Vrati collapsed rod redak (sakupljeno stanje)
@app.get("/collapse-rod/{rod_slug}", response_class=HTMLResponse)
def collapse_rod(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    return f"""
    <tr id="rod-{rod_slug}" class="rod-row">
      <td>
        {rod}
        <span style="float:right; cursor:pointer;" 
              hx-get="/expand-rod/{rod_slug}" 
              hx-target="#rod-{rod_slug}" 
              hx-swap="outerHTML">▼</span>
      </td>
    </tr>
    """

# Vrati expanded rod redak – s redovima za skupine ispod rod retka
@app.get("/expand-rod/{rod_slug}", response_class=HTMLResponse)
def expand_rod(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    skupine_lista = sorted(list(rodovi.get(rod, [])))
    # Prvi redak: rod sa collapse gumbom
    html = f"""
    <tr id="rod-{rod_slug}" class="rod-row">
      <td>
        {rod}
        <span style="float:right; cursor:pointer;" 
              hx-get="/collapse-rod/{rod_slug}" 
              hx-target="#rod-{rod_slug}" 
              hx-swap="outerHTML">▲</span>
      </td>
    </tr>
    """
    # Dodaj retke za svaku skupinu (collapsed)
    for skupina in skupine_lista:
        skupina_slug = slugify(skupina)
        html += f"""
        <tr id="group-{skupina_slug}" class="group-row">
          <td style="padding-left:1em;">
            {skupina}
            <span style="float:right; cursor:pointer;" 
                  hx-get="/expand-group/{skupina_slug}" 
                  hx-target="#group-{skupina_slug}" 
                  hx-swap="outerHTML">▼</span>
          </td>
        </tr>
        """
    return html

# --- SKUPINE ---

# Vrati collapsed group redak (sakupljeno stanje skupine)
@app.get("/collapse-group/{group_slug}", response_class=HTMLResponse)
def collapse_group(request: Request, group_slug: str):
    group = get_skupina_by_slug(group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    return f"""
    <tr id="group-{group_slug}" class="group-row">
      <td style="padding-left:1em;">
        {group}
        <span style="float:right; cursor:pointer;" 
              hx-get="/expand-group/{group_slug}" 
              hx-target="#group-{group_slug}" 
              hx-swap="outerHTML">▼</span>
      </td>
    </tr>
    """

# Vrati expanded group redak – s retcima za zanimanja ispod
@app.get("/expand-group/{group_slug}", response_class=HTMLResponse)
def expand_group(request: Request, group_slug: str):
    group = get_skupina_by_slug(group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    lista_zanimanja = skupine.get(group, [])
    # Prvi redak: skupina sa collapse gumbom
    html = f"""
    <tr id="group-{group_slug}" class="group-row">
      <td style="padding-left:1em;">
        {group}
        <span style="float:right; cursor:pointer;" 
              hx-get="/collapse-group/{group_slug}" 
              hx-target="#group-{group_slug}" 
              hx-swap="outerHTML">▲</span>
      </td>
    </tr>
    """
    # Dodaj retke za svako zanimanje (collapsed, bez opisa)
    for z in lista_zanimanja:
        sifra = z["sifra"]
        ime = z["ime"]
        html += f"""
        <tr id="occ-{sifra}" class="occupation-row">
          <td style="padding-left:2em;">
            {sifra} {ime}
            <span style="float:right; cursor:pointer;" 
                  hx-get="/toggle/{sifra}" 
                  hx-target="#occ-{sifra}" 
                  hx-swap="outerHTML">▼</span>
          </td>
        </tr>
        """
    return html

# --- ZANIMANJA OPIS ---

# Toggle – prikazuje opis zanimanja (expanded) ili se vraća u collapsed stanje
@app.get("/toggle/{code}", response_class=HTMLResponse)
def toggle_opis(request: Request, code: str):
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    opis = zan_dict[code]["description"]
    ime = zan_dict[code]["ime"]
    # Expanded state: prikazuje opis i collapse gumb
    return f"""
    <tr id="occ-{code}" class="occupation-row">
      <td style="padding-left:2em;">
        {code} {ime}
        <span style="float:right; cursor:pointer;" 
              hx-get="/hide/{code}" 
              hx-target="#occ-{code}" 
              hx-swap="outerHTML">▲</span>
        <div class="opis">{opis}</div>
      </td>
    </tr>
    """

@app.get("/hide/{code}", response_class=HTMLResponse)
def hide_opis(request: Request, code: str):
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    ime = zan_dict[code]["ime"]
    sifra = code
    # Collapsed state: prikazuje osnovne podatke i expand gumb
    return f"""
    <tr id="occ-{code}" class="occupation-row">
      <td style="padding-left:2em;">
        {sifra} {ime}
        <span style="float:right; cursor:pointer;" 
              hx-get="/toggle/{code}" 
              hx-target="#occ-{code}" 
              hx-swap="outerHTML">▼</span>
      </td>
    </tr>
    """

@app.get("/test", response_class=HTMLResponse)
def test(request: Request):
    return "<tr><td>Test uspješan!</td></tr>"
