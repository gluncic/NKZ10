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
    Normalizira tekst, uklanja dijakritike i nealfanumeričke znakove,
    zamjenjuje razmake s crticama (lowercase).
    """
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[-\s]+", "-", value)
    return value

# Pomoćne funkcije za pronalaženje originalnog roda ili skupine
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

# ---------------------------
# Učitavanje JSON-a
# ---------------------------
with open("NKZ_descriptions_chatGPT4omini.json", encoding="utf-8") as f:
    zan_dict = json.load(f)

rodovi = {}    # npr. rodovi[rod] = {skupina1, skupina2, ...}
skupine = {}   # npr. skupine[skupina] = [ { "sifra": ..., "ime": ... }, ... ]

for sifra, data in zan_dict.items():
    rod = data["rod"]
    skupina = data["skupina"]
    rodovi.setdefault(rod, set()).add(skupina)
    skupine.setdefault(skupina, []).append({
        "sifra": sifra,
        "ime": data["ime"]
    })

# ---------------------------
# Početna stranica
# ---------------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # Sortiramo rodove i njihovu listu skupina
    rods = []
    for rod, skupine_set in rodovi.items():
        rods.append({
            "rod": rod,
            "slug": slugify(rod),
            "skupine": sorted(list(skupine_set))
        })
    rods.sort(key=lambda x: x["rod"])
    return templates.TemplateResponse("index.html", {"request": request, "rods": rods})

# ---------------------------
# Ekspanzija 1: Klik na rod
# ---------------------------
@app.get("/expand-rod/{rod_slug}", response_class=HTMLResponse)
def expand_rod(request: Request, rod_slug: str):
    """
    Ubacuje retke za sve skupine ispod retka odabranog roda + jedan 'Sakrij rod' redak.
    """
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")

    skupine_lista = sorted(list(rodovi.get(rod, [])))
    # 1) Redak "Sakrij rod" s linkom koji briše te retke
    html = f"""
    <tr id="row-hide-rod-{rod_slug}">
      <td>
        <a href="#" hx-target="#row-hide-rod-{rod_slug}" hx-swap="delete">
          Sakrij rod
        </a>
      </td>
    </tr>
    """
    # 2) Retci za svaku skupinu
    for skupina in skupine_lista:
        skupina_slug = slugify(skupina)
        html += f"""
        <tr id="row-group-{skupina_slug}">
          <td>
            <a href="#"
               hx-get="/expand-group/{skupina_slug}"
               hx-target="#row-group-{skupina_slug}"
               hx-swap="afterend">
               &nbsp;{skupina}
            </a>
          </td>
        </tr>
        """
    return html

# ---------------------------
# Ekspanzija 2: Klik na skupinu
# ---------------------------
@app.get("/expand-group/{skupina_slug}", response_class=HTMLResponse)
def expand_group(request: Request, skupina_slug: str):
    """
    Ubacuje redak "Sakrij skupinu" + retke za svako zanimanje ispod retka skupine.
    """
    skupina = get_skupina_by_slug(skupina_slug)
    if not skupina:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")

    lista_zanimanja = skupine.get(skupina, [])
    # 1) Redak "Sakrij skupinu"
    html = f"""
    <tr id="row-hide-group-{skupina_slug}">
      <td>
        <a href="#"
           hx-target="#row-hide-group-{skupina_slug}"
           hx-swap="delete">
           &nbsp;Sakrij skupinu
        </a>
      </td>
    </tr>
    """
    # 2) Retci za zanimanja
    for z in lista_zanimanja:
        sifra = z["sifra"]
        ime = z["ime"]
        html += f"""
        <tr id="row-occ-{sifra}">
          <td>
            {sifra}
            <a href="#"
               hx-get="/toggle/{sifra}"
               hx-target="#row-occ-{sifra}"
               hx-swap="outerHTML">
               &nbsp;{ime}
            </a>
          </td>
        </tr>
        """
    return html

# ---------------------------
# Ekspanzija 3: Klik na zanimanje – toggle opis
# ---------------------------
@app.get("/toggle/{code}", response_class=HTMLResponse)
def toggle_opis(request: Request, code: str):
    """
    Zamjenjuje redak zanimanja s redkom koji sadrži opis (ili obrnuto).
    """
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    opis = zan_dict[code]["description"]
    ime = zan_dict[code]["ime"]

    return f"""
    <tr id="row-occ-{code}">
      <td>
        <a href="#" hx-get="/hide/{code}" hx-target="#row-occ-{code}" hx-swap="outerHTML">
          {ime}
        </a>
        <div class="opis">{opis}</div>
      </td>
    </tr>
    """

@app.get("/hide/{code}", response_class=HTMLResponse)
def hide_opis(request: Request, code: str):
    """
    Vraća se osnovni redak bez opisa.
    """
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    ime = zan_dict[code]["ime"]
    sifra = code
    return f"""
    <tr id="row-occ-{code}">
      <td>
        {sifra}
        <a href="#" hx-get="/toggle/{code}" hx-target="#row-occ-{code}" hx-swap="outerHTML">
           &nbsp;{ime}
        </a>
      </td>
    </tr>
    """

@app.get("/test", response_class=HTMLResponse)
def test(request: Request):
    return "<tr><td>Test uspješan!</td></tr>"
