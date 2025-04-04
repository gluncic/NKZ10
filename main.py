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
    Normalizira tekst, uklanja dijakritike i nealfanumeričke znakove te zamjenjuje razmake s crticama (lowercase).
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

# Početna stranica – svaki rod u svom <tbody>
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

# --- Rod ---
# Klikom na rod (koji je u svom tbody) mijenjamo sadržaj tog tbody-a – dodajemo redak za rod i za svaku skupinu.
@app.get("/skupine/{rod_slug}", response_class=HTMLResponse)
def prikazi_skupine(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    skupine_lista = sorted(list(rodovi.get(rod, [])))
    html = f"""
    <tr class="rod-row">
      <td></td>
      <td>
        <a href="#" hx-get="/sakrij-rod/{rod_slug}" hx-target="#tbody-{rod_slug}" hx-swap="innerHTML">
           {rod}
        </a>
      </td>
    </tr>
    """
    for skupina in skupine_lista:
        skupina_slug = slugify(skupina)
        # Za skupine koristimo hx-target na sam redak
        html += f"""
        <tr id="skupina-{skupina_slug}" class="group-row">
          <td></td>
          <td>
            <a href="#" hx-get="/zanimanja/{skupina_slug}" hx-target="#skupina-{skupina_slug}" hx-swap="outerHTML">
               &nbsp;{skupina}
            </a>
          </td>
        </tr>
        """
    return html

# Vraćanje rodovog retka (sakriva skupine)
@app.get("/sakrij-rod/{rod_slug}", response_class=HTMLResponse)
def sakrij_rod(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    return f"""
    <tr class="rod-row">
      <td></td>
      <td>
        <a href="#" hx-get="/skupine/{rod_slug}" hx-target="#tbody-{rod_slug}" hx-swap="innerHTML">
           {rod}
        </a>
      </td>
    </tr>
    """

# --- Skupina i zanimanja ---
# Klikom na skupinu mijenjamo sadržaj samo tog redka (skupina) – dodajemo ispod njega redove za zanimanja.
@app.get("/zanimanja/{skupina_slug}", response_class=HTMLResponse)
def prikazi_zanimanja(request: Request, skupina_slug: str):
    skupina = get_skupina_by_slug(skupina_slug)
    if not skupina:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    lista_zanimanja = skupine.get(skupina, [])
    html = f"""
    <tr id="skupina-{skupina_slug}" class="group-row">
      <td></td>
      <td>
        <a href="#" hx-get="/sakrij-skupinu/{skupina_slug}" hx-target="#skupina-{skupina_slug}" hx-swap="outerHTML">
           &nbsp;{skupina}
        </a>
      </td>
    </tr>
    """
    for z in lista_zanimanja:
        sifra = z["sifra"]
        ime = z["ime"]
        html += f"""
        <tr id="blok-{sifra}" class="occupation-row">
          <td>{sifra}</td>
          <td>
            <a href="#" hx-get="/toggle/{sifra}" hx-target="#blok-{sifra}" hx-swap="outerHTML">
               &nbsp;&nbsp;{ime}
            </a>
          </td>
        </tr>
        """
    return html

# Vraćanje skupinog retka (sakriva zanimanja)
@app.get("/sakrij-skupinu/{skupina_slug}", response_class=HTMLResponse)
def sakrij_skupinu(request: Request, skupina_slug: str):
    skupina = get_skupina_by_slug(skupina_slug)
    if not skupina:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    return f"""
    <tr id="skupina-{skupina_slug}" class="group-row">
      <td></td>
      <td>
        <a href="#" hx-get="/zanimanja/{skupina_slug}" hx-target="#skupina-{skupina_slug}" hx-swap="outerHTML">
           &nbsp;{skupina}
        </a>
      </td>
    </tr>
    """

# --- Zanimanje opis ---
# Klikom na zanimanje (koji je cijeli redak) mijenjamo samo taj redak s opisom.
@app.get("/toggle/{code}", response_class=HTMLResponse)
def toggle_opis(request: Request, code: str):
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    opis = zan_dict[code]["description"]
    ime = zan_dict[code]["ime"]
    return f"""
    <tr id="blok-{code}" class="occupation-row">
      <td>{code}</td>
      <td>
        <a href="#" hx-get="/sakrij/{code}" hx-target="#blok-{code}" hx-swap="outerHTML">
           {ime}
        </a>
        <div class="opis">{opis}</div>
      </td>
    </tr>
    """

# Vraćanje zanimanja (sakriva opis)
@app.get("/sakrij/{code}", response_class=HTMLResponse)
def sakrij_opis(request: Request, code: str):
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    ime = zan_dict[code]["ime"]
    return f"""
    <tr id="blok-{code}" class="occupation-row">
      <td>{code}</td>
      <td>
        <a href="#" hx-get="/toggle/{code}" hx-target="#blok-{code}" hx-swap="outerHTML">
           {ime}
        </a>
      </td>
    </tr>
    """

@app.get("/test", response_class=HTMLResponse)
def test(request: Request):
    return "<tr><td></td><td>Test uspješan!</td></tr>"
