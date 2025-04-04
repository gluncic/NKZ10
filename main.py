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
    Normalizira tekst, uklanja dijakritike i nealfanumeričke znakove te zamjenjuje razmake s crticama.
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

# Grupiranje podataka:
# - rodovi: { rod: set(skupina, ...), ... }
# - skupine: { skupina: [ { "sifra": ..., "ime": ... }, ... ], ... }
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

# Ekspanzija 1: Klik na rod – vraća HTML fragment s rod linkom i popisom skupina
@app.get("/skupine/{rod_slug}", response_class=HTMLResponse)
def prikazi_skupine(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    skupine_lista = sorted(list(rodovi.get(rod, [])))
    # Vraćamo fragment koji će zamijeniti sadržaj <div> unutar ćelije
    html = f"""
    <div id="row-rod-{rod_slug}" class="rod-row">
      <a href="#" hx-get="/sakrij-rod/{rod_slug}" hx-target="#row-rod-{rod_slug}" hx-swap="outerHTML">
         {rod}
      </a>
    </div>
    """
    for skupina in skupine_lista:
        skupina_slug = slugify(skupina)
        html += f"""
        <div id="row-group-{skupina_slug}" class="group-row" style="margin-left: 1em;">
          <a href="#" hx-get="/zanimanja/{skupina_slug}" hx-target="#row-group-{skupina_slug}" hx-swap="outerHTML">
             {skupina}
          </a>
        </div>
        """
    return html

@app.get("/sakrij-rod/{rod_slug}", response_class=HTMLResponse)
def sakrij_rod(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    return f"""
    <div id="row-rod-{rod_slug}" class="rod-row">
      <a href="#" hx-get="/skupine/{rod_slug}" hx-target="#row-rod-{rod_slug}" hx-swap="outerHTML">
         {rod}
      </a>
    </div>
    """

# Ekspanzija 2: Klik na skupinu – vraća fragment s linkom skupine i popisom zanimanja
@app.get("/zanimanja/{skupina_slug}", response_class=HTMLResponse)
def prikazi_zanimanja(request: Request, skupina_slug: str):
    skupina = get_skupina_by_slug(skupina_slug)
    if not skupina:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    lista_zanimanja = skupine.get(skupina, [])
    html = f"""
    <div id="row-group-{skupina_slug}" class="group-row" style="margin-left: 1em;">
      <a href="#" hx-get="/sakrij-skupinu/{skupina_slug}" hx-target="#row-group-{skupina_slug}" hx-swap="outerHTML">
         {skupina}
      </a>
    </div>
    """
    for z in lista_zanimanja:
        sifra = z["sifra"]
        ime = z["ime"]
        html += f"""
        <div id="row-occ-{sifra}" class="occupation-row" style="margin-left: 2em;">
            <a href="#" hx-get="/toggle/{sifra}" hx-target="#row-occ-{sifra}" hx-swap="outerHTML">
              {sifra} {ime}
            </a>
        </div>
        """
    return html

@app.get("/sakrij-skupinu/{skupina_slug}", response_class=HTMLResponse)
def sakrij_skupinu(request: Request, skupina_slug: str):
    skupina = get_skupina_by_slug(skupina_slug)
    if not skupina:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    return f"""
    <div id="row-group-{skupina_slug}" class="group-row" style="margin-left: 1em;">
      <a href="#" hx-get="/zanimanja/{skupina_slug}" hx-target="#row-group-{skupina_slug}" hx-swap="outerHTML">
         {skupina}
      </a>
    </div>
    """

# Ekspanzija 3: Klik na zanimanje – otvara opis zanimanja
@app.get("/toggle/{code}", response_class=HTMLResponse)
def toggle_opis(request: Request, code: str):
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    opis = zan_dict[code]["description"]
    ime = zan_dict[code]["ime"]
    return f"""
    <div id="row-occ-{code}" class="occupation-row" style="margin-left: 2em;">
      <a href="#" hx-get="/sakrij/{code}" hx-target="#row-occ-{code}" hx-swap="outerHTML">
         {code} {ime}
      </a>
      <div class="opis">{opis}</div>
    </div>
    """

@app.get("/sakrij/{code}", response_class=HTMLResponse)
def sakrij_opis(request: Request, code: str):
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    ime = zan_dict[code]["ime"]
    return f"""
    <div id="row-occ-{code}" class="occupation-row" style="margin-left: 2em;">
      <a href="#" hx-get="/toggle/{code}" hx-target="#row-occ-{code}" hx-swap="outerHTML">
         {code} {ime}
      </a>
    </div>
    """

@app.get("/test", response_class=HTMLResponse)
def test(request: Request):
    return "<div>Test uspješan!</div>"
