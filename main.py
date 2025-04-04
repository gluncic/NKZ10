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

# Učitavanje podataka iz JSON datoteke
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

# Ekspanzija 1: Klik na rod – vraća redak za rod i retke za skupine
@app.get("/skupine/{rod_slug}", response_class=HTMLResponse)
def prikazi_skupine(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    skupine_lista = sorted(list(rodovi.get(rod, [])))
    html = f"""
    <tr id="rod-{rod_slug}" class="rod-row">
      <td></td>
      <td>
        <a href="#"
           hx-get="/sakrij-rod/{rod_slug}"
           hx-target="#rod-{rod_slug}"
           hx-swap="outerHTML">
           {rod}
        </a>
      </td>
    </tr>
    """
    for skupina in skupine_lista:
        skupina_slug = slugify(skupina)
        html += f"""
        <tr id="skupina-{skupina_slug}" class="group-row">
          <td></td>
          <td>
            <a href="#"
               hx-get="/zanimanja/{skupina_slug}"
               hx-target="#skupina-{skupina_slug}"
               hx-swap="outerHTML">
               {skupina}
            </a>
          </td>
        </tr>
        """
    return html

@app.get("/sakrij-rod/{rod_slug}", response_class=HTMLResponse)
def sakrij_rod(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    return f"""
    <tr id="rod-{rod_slug}" class="rod-row">
      <td></td>
      <td>
        <a href="#"
           hx-get="/skupine/{rod_slug}"
           hx-target="#rod-{rod_slug}"
           hx-swap="outerHTML">
           {rod}
        </a>
      </td>
    </tr>
    """

# Ekspanzija 2: Klik na skupinu – vraća redak za skupinu i redove za zanimanja
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
        <a href="#"
           hx-get="/sakrij-skupinu/{skupina_slug}"
           hx-target="#skupina-{skupina_slug}"
           hx-swap="outerHTML">
           {skupina}
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
            <div id="content-{sifra}">
              <a href="#"
                 hx-get="/toggle/{sifra}"
                 hx-target="#content-{sifra}"
                 hx-swap="outerHTML">
                 {ime}
              </a>
            </div>
          </td>
        </tr>
        """
    return html

@app.get("/sakrij-skupinu/{skupina_slug}", response_class=HTMLResponse)
def sakrij_skupinu(request: Request, skupina_slug: str):
    skupina = get_skupina_by_slug(skupina_slug)
    if not skupina:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    return f"""
    <tr id="skupina-{skupina_slug}" class="group-row">
      <td></td>
      <td>
        <a href="#"
           hx-get="/zanimanja/{skupina_slug}"
           hx-target="#skupina-{skupina_slug}"
           hx-swap="outerHTML">
           {skupina}
        </a>
      </td>
    </tr>
    """

# Ekspanzija 3: Klik na zanimanje – otvara opis zanimanja
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
        <div id="content-{code}">
          <a href="#"
             hx-get="/sakrij/{code}"
             hx-target="#content-{code}"
             hx-swap="outerHTML">
             {ime}
          </a>
          <div class="opis">{opis}</div>
        </div>
      </td>
    </tr>
    """

@app.get("/sakrij/{code}", response_class=HTMLResponse)
def sakrij_opis(request: Request, code: str):
    if code not in zan_dict:
        raise HTTPException(status_code=404, detail="Zanimanje nije pronađeno")
    ime = zan_dict[code]["ime"]
    return f"""
    <tr id="blok-{code}" class="occupation-row">
      <td>{code}</td>
      <td>
        <div id="content-{code}">
          <a href="#"
             hx-get="/toggle/{code}"
             hx-target="#content-{code}"
             hx-swap="outerHTML">
             {ime}
          </a>
        </div>
      </td>
    </tr>
    """

@app.get("/test", response_class=HTMLResponse)
def test(request: Request):
    return "<tr><td></td><td>Test uspješan!</td></tr>"
