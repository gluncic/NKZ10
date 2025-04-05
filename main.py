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
    Normalizira tekst, uklanja dijakritike i nealfanumeričke znakove
    te zamjenjuje razmake s crticama (lowercase).
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

# -----------------------------------------
# Učitavanje i grupiranje podataka iz JSON
# -----------------------------------------
with open("NKZ_descriptions_chatGPT4omini.json", encoding="utf-8") as f:
    zan_dict = json.load(f)

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

# -----------------------------------------
# Početna stranica – prikazuje rodove
# -----------------------------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    rods = []
    for rod, skupine_set in rodovi.items():
        rods.append({
            "rod": rod,
            "slug": slugify(rod),
            "skupine": sorted(list(skupine_set))
        })
    rods.sort(key=lambda x: x["rod"])
    return templates.TemplateResponse("index.html", {"request": request, "rods": rods})

# ------------------------------------------------------------------
# Rodovi – collapsed (prikaže se samo rod) i expanded (rod + skupine)
# ------------------------------------------------------------------

@app.get("/expand-rod/{rod_slug}", response_class=HTMLResponse)
def expand_rod(request: Request, rod_slug: str):
    """Klik na rod – prikazuje rod + skupine (collapsed)."""
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    skupine_lista = sorted(list(rodovi[rod]))

    # 1) Prvi redak: rod s linkom za collapse
    html = f"""
    <tr id="rod-{rod_slug}" class="rod-row">
      <td>
        <span class="rod-link">{rod}</span>
        <a class="collapse-rod" href="#"
           hx-get="/collapse-rod/{rod_slug}"
           hx-target="#rod-{rod_slug}"
           hx-swap="outerHTML">
           (Sakrij)
        </a>
      </td>
    </tr>
    """
    # 2) Redci za skupine (u collapsed stanju)
    for skupina in skupine_lista:
        skupina_slug = slugify(skupina)
        html += f"""
        <tr id="skupina-{skupina_slug}" class="group-row">
          <td style="padding-left:20px;">
            <a class="skupina-link" href="#"
               hx-get="/expand-group/{skupina_slug}"
               hx-target="#skupina-{skupina_slug}"
               hx-swap="outerHTML">
               {skupina}
            </a>
          </td>
        </tr>
        """
    return html

@app.get("/collapse-rod/{rod_slug}", response_class=HTMLResponse)
def collapse_rod(request: Request, rod_slug: str):
    """Klik na (Sakrij) – vraća rod u početno (collapsed) stanje."""
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    # Kao u index.html: jedan redak s linkom za expand
    return f"""
    <tr id="rod-{rod_slug}" class="rod-row">
      <td>
        <a class="rod-link" href="#"
           hx-get="/expand-rod/{rod_slug}"
           hx-target="#rod-{rod_slug}"
           hx-swap="outerHTML">
           {rod}
        </a>
      </td>
    </tr>
    """

# -------------------------------------------
# Skupine – collapsed i expanded (prikazuje zanimanja)
# -------------------------------------------

@app.get("/expand-group/{group_slug}", response_class=HTMLResponse)
def expand_group(request: Request, group_slug: str):
    """Klik na skupinu – prikazuje skupinu s linkom za sakrivanje i retke za zanimanja."""
    skupina = get_skupina_by_slug(group_slug)
    if not skupina:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    lista_zanimanja = skupine[skupina]

    # 1) Prvi redak: skupina s linkom (Sakrij)
    html = f"""
    <tr id="skupina-{group_slug}" class="group-row">
      <td style="padding-left:20px;">
        <span class="skupina-link">{skupina}</span>
        <a class="collapse-group" href="#"
           hx-get="/collapse-group/{group_slug}"
           hx-target="#skupina-{group_slug}"
           hx-swap="outerHTML">
           (Sakrij)
        </a>
      </td>
    </tr>
    """
    # 2) Redci za zanimanja (collapsed)
    for z in lista_zanimanja:
        code = z["sifra"]
        ime = z["ime"]
        html += f"""
        <tr id="occ-{code}" class="occupation-row">
          <td style="padding-left:20px;">
            <a class="zanimanje-link" href="#"
               hx-get="/expand-occ/{code}"
               hx-target="#occ-{code}"
               hx-swap="outerHTML">
               {ime}
            </a>
          </td>
        </tr>
        """
    return html

@app.get("/collapse-group/{group_slug}", response_class=HTMLResponse)
def collapse_group(request: Request, group_slug: str):
    """Klik na (Sakrij) skupine – vraća skupinu u collapsed stanje."""
    group = get_skupina_by_slug(group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    return f"""
    <tr id="skupina-{group_slug}" class="group-row">
      <td style="padding-left:20px;">
        <a class="skupina-link" href="#"
           hx-get="/expand-group/{group_slug}"
           hx-target="#skupina-{group_slug}"
           hx-swap="outerHTML">
           {group}
        </a>
      </td>
    </tr>
    """

# -------------------------------------------
# Zanimanja – collapsed i expanded (prikazuje opis)
# -------------------------------------------

@app.get("/expand-occ/{code}", response_class=HTMLResponse)
def expand_occ(request: Request, code: str):
    """Klik na zanimanje – prikazuje opis."""
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    opis = zan_dict[code]["description"]
    ime = zan_dict[code]["ime"]
    return f"""
    <tr id="occ-{code}" class="occupation-row">
      <td style="padding-left:20px;">
        <span class="zanimanje-link">{ime}</span>
        <a class="collapse-occ" href="#"
           hx-get="/collapse-occ/{code}"
           hx-target="#occ-{code}"
           hx-swap="outerHTML">
           (Sakrij opis)
        </a>
        <div class="opis">{opis}</div>
      </td>
    </tr>
    """

@app.get("/collapse-occ/{code}", response_class=HTMLResponse)
def collapse_occ(request: Request, code: str):
    """Klik na (Sakrij opis) – vraća zanimanje u collapsed stanje."""
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    ime = zan_dict[code]["ime"]
    return f"""
    <tr id="occ-{code}" class="occupation-row">
      <td style="padding-left:20px;">
        <a class="zanimanje-link" href="#"
           hx-get="/expand-occ/{code}"
           hx-target="#occ-{code}"
           hx-swap="outerHTML">
           {ime}
        </a>
      </td>
    </tr>
    """

@app.get("/test", response_class=HTMLResponse)
def test(request: Request):
    return "<tr><td>Test uspješan!</td></tr>"
