import re
import unicodedata
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json

app = FastAPI()
# Provjeri da folder "static" postoji ili promijeni putanju
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def slugify(value: str) -> str:
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

with open("NKZ_descriptions_chatGPT4omini.json", encoding="utf-8") as f:
    zan_dict = json.load(f)

# rodovi = {}
# skupine = {}
# for sifra, data in zan_dict.items():
#     rod = data["rod"]
#     skupina = data["skupina"]
#     rodovi.setdefault(rod, set()).add(skupina)
#     skupine.setdefault(skupina, []).append({
#         "sifra": sifra,
#         "ime": data["ime"]
#     })
rodovi = {}
skupine = {}
for sifra, data in zan_dict.items():
    ime = f"{sifra} {data['ime']}"
    modified_skupina = f"{sifra[:4]} {data['skupina']}"
    modified_rod = f"{sifra[0]} {data['rod']}"

    rodovi.setdefault(modified_rod, set()).add(modified_skupina)
    skupine.setdefault(modified_skupina, []).append({
        "sifra": sifra,
        "ime": ime
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


# ----- RODOVI -----
@app.get("/expand-rod/{rod_slug}", response_class=HTMLResponse)
def expand_rod(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    groups = sorted(list(rodovi[rod]))
    html = f"""
     <table id="table-{rod_slug}">
      <thead>
        <tr class="rod-row">
         <th class="rod-link" href="#"
             hx-get="/collapse-rod/{rod_slug}"
             hx-target="#table-{rod_slug}"
             hx-swap="outerHTML">
            {rod}
         </th>
       </tr>
      </thead>
    """
    # Za svaku grupu stvaramo zaseban <tbody> s odgovarajućim ID-jem
    for group in groups:
        group_slug = slugify(group)
        html += f"""
      <tbody id="tbody-group-{group_slug}">
        <tr class="group-row">
          <td>
            <a class="skupina-link" href="#"
               hx-get="/expand-group/{group_slug}"
               hx-target="#tbody-group-{group_slug}"
               hx-swap="innerHTML">
              {group}
            </a>
          </td>
        </tr>
      </tbody>
        """
    html += "</table>"
    return html

@app.get("/collapse-rod/{rod_slug}", response_class=HTMLResponse)
def collapse_rod(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)

    # Vraćamo originalni collapsed HTML (samo jedan redak) unutar tbody-ja
    return f"""
     <table id="table-{rod_slug}">
      <thead>
        <tr class="rod-row">
         <th class="rod-link" href="#" hx-get="/expand-rod/{rod_slug}" hx-target="#table-{rod_slug}" hx-swap="innerHTML">{rod}
         </th>
       </tr>
      </thead>
     <tbody></tbody></table>
     """""

# ----- SKUPINE -----

@app.get("/expand-group/{group_slug}", response_class=HTMLResponse)
def expand_group(request: Request, group_slug: str):
    group = get_skupina_by_slug(group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    occs = skupine.get(group, [])
    html = f"""
      <tr class="group-row">
        <td>
          <a class="skupina-link" href="#"
             hx-get="/collapse-group/{group_slug}"
             hx-target="#tbody-group-{group_slug}"
             hx-swap="innerHTML">
            {group}
          </a>
        </td>
      </tr>
    """
    for occ in occs:
        code = occ["sifra"]
        name = occ["ime"]
        html += f"""
      <tr id="occ-{code}" class="occupation-row">
        <td style="padding-left:40px;">
          <a class="zanimanje-link" href="#"
             hx-get="/expand-occ/{code}"
             hx-target="#occ-{code}"
             hx-swap="outerHTML">
            {name}
          </a>
        </td>
      </tr>
        """
    return html

@app.get("/collapse-group/{group_slug}", response_class=HTMLResponse)
def collapse_group(request: Request, group_slug: str):
    group = get_skupina_by_slug(group_slug)
    return f"""
      <tr class="group-row">
        <td>
          <a class="skupina-link" href="#"
             hx-get="/expand-group/{group_slug}"
             hx-target="#tbody-group-{group_slug}"
             hx-swap="innerHTML">
            {group}
          </a>
        </td>
      </tr>
    """
# ----- ZANIMANJA -----

@app.get("/expand-occ/{code}", response_class=HTMLResponse)
def expand_occ(request: Request, code: str):
    opis = zan_dict[code]["description"]
    name = zan_dict[code]["ime"]
    ocname = f"{code} {name}"
    return f"""
    <tr id="occ-{code}" class="occupation-row">
      <td style="padding-left:40px;">
        <a class="zanimanje-link" href="#" hx-get="/collapse-occ/{code}" hx-target="#occ-{code}" hx-swap="outerHTML">{ocname}</a>
        <div class="opis">{opis}</div>
      </td>
    </tr>
    """

@app.get("/collapse-occ/{code}", response_class=HTMLResponse)
def collapse_occ(request: Request, code: str):
    name = zan_dict[code]["ime"]
    ocname = f"{code} {name}"
    return f"""
    <tr id="occ-{code}" class="occupation-row">
      <td style="padding-left:40px;">
        <a class="zanimanje-link" href="#" hx-get="/expand-occ/{code}" hx-target="#occ-{code}" hx-swap="outerHTML">{ocname}</a>
      </td>
    </tr>
    """

@app.get("/test", response_class=HTMLResponse)
def test(request: Request):
    return "<tr><td>Test uspješan!</td></tr>"
