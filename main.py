from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
from urllib.parse import quote, unquote

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Učitavanje podataka iz JSON datoteke
with open("NKZ_descriptions_chatGPT4omini.json", encoding="utf-8") as f:
    zan_dict = json.load(f)

# Grupiranje po rodovima i skupinama
rodovi = {}
skupine = {}

for sifra, data in zan_dict.items():
    if "rod" not in data or "skupina" not in data:
        print(f"Warning: zapis {sifra} nema rod ili skupinu")
        continue
    rod = data["rod"]
    skupina = data["skupina"]
    rodovi.setdefault(rod, set()).add(skupina)
    skupine.setdefault(skupina, []).append({
        "sifra": sifra,
        "ime": data["ime"]
    })

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # Priprema liste rodova s njihovim URL-enkodiranim varijantama
    rods = []
    for rod, skupina_set in rodovi.items():
        rods.append({
            "rod": rod,
            "encoded": quote(rod),
            "skupine": sorted(list(skupina_set))
        })
    rods.sort(key=lambda x: x["rod"])
    return templates.TemplateResponse("index.html", {"request": request, "rods": rods})

@app.get("/skupine/{rod}", response_class=HTMLResponse)
def prikazi_skupine(request: Request, rod: str):
    rod = unquote(rod)
    print("prikazi_skupine pozvan za rod:", rod)
    rod_enc = quote(rod)
    skupine_lista = sorted(list(rodovi.get(rod, [])))
    html = f"<div id='rod-{rod_enc}' class='blok'>"
    html += f"<div class='rod' hx-get='/sakrij-rod/{rod_enc}' hx-target='#rod-{rod_enc}' hx-swap='outerHTML' hx-trigger='click'>{rod}</div>"
    for skupina in skupine_lista:
        skupina_enc = quote(skupina)
        html += f"<div id='skupina-{skupina_enc}' class='blok'>"
        html += f"<div class='skupina' hx-get='/zanimanja/{skupina_enc}' hx-target='#skupina-{skupina_enc}' hx-swap='outerHTML' hx-trigger='click'>{skupina}</div>"
        html += "</div>"
    html += "</div>"
    return html

@app.get("/sakrij-rod/{rod}", response_class=HTMLResponse)
def sakrij_rod(request: Request, rod: str):
    rod = unquote(rod)
    print("sakrij_rod pozvan za rod:", rod)
    rod_enc = quote(rod)
    html = f"<div id='rod-{rod_enc}' class='blok'>"
    html += f"<div class='rod' hx-get='/skupine/{rod_enc}' hx-target='#rod-{rod_enc}' hx-swap='outerHTML' hx-trigger='click'>{rod}</div>"
    html += "</div>"
    return html

@app.get("/zanimanja/{skupina}", response_class=HTMLResponse)
def prikazi_zanimanja(request: Request, skupina: str):
    skupina = unquote(skupina)
    print("prikazi_zanimanja pozvan za skupina:", skupina)
    skupina_enc = quote(skupina)
    zanimanja = skupine.get(skupina, [])
    html = f"<div id='skupina-{skupina_enc}' class='blok'>"
    html += f"<div class='skupina' hx-get='/sakrij-skupinu/{skupina_enc}' hx-target='#skupina-{skupina_enc}' hx-swap='outerHTML' hx-trigger='click'>{skupina}</div>"
    for z in zanimanja:
        sifra = z['sifra']
        ime = z['ime']
        html += f"<div id='blok-{sifra}' class='zanimanje-blok'>"
        html += f"<div class='zanimanje' hx-get='/toggle/{sifra}' hx-target='#blok-{sifra}' hx-swap='outerHTML' hx-trigger='click'>{ime}</div>"
        html += "</div>"
    html += "</div>"
    return html

@app.get("/sakrij-skupinu/{skupina}", response_class=HTMLResponse)
def sakrij_skupinu(request: Request, skupina: str):
    skupina = unquote(skupina)
    print("sakrij_skupinu pozvan za skupina:", skupina)
    skupina_enc = quote(skupina)
    html = f"<div id='skupina-{skupina_enc}' class='blok'>"
    html += f"<div class='skupina' hx-get='/zanimanja/{skupina_enc}' hx-target='#skupina-{skupina_enc}' hx-swap='outerHTML' hx-trigger='click'>{skupina}</div>"
    html += "</div>"
    return html

@app.get("/toggle/{code}", response_class=HTMLResponse)
def toggle_opis(request: Request, code: str):
    print("toggle_opis pozvan za code:", code)
    opis = zan_dict[code]["description"]
    ime = zan_dict[code]["ime"]
    html = f"<div id='blok-{code}' class='zanimanje-blok'>"
    html += f"<div class='zanimanje' hx-get='/sakrij/{code}' hx-target='#blok-{code}' hx-swap='outerHTML' hx-trigger='click'>{ime}</div>"
    html += f"<div class='opis'>{opis}</div>"
    html += "</div>"
    return html

@app.get("/sakrij/{code}", response_class=HTMLResponse)
def sakrij_opis(request: Request, code: str):
    print("sakrij_opis pozvan za code:", code)
    ime = zan_dict[code]["ime"]
    html = f"<div id='blok-{code}' class='zanimanje-blok'>"
    html += f"<div class='zanimanje' hx-get='/toggle/{code}' hx-target='#blok-{code}' hx-swap='outerHTML' hx-trigger='click'>{ime}</div>"
    html += "</div>"
    return html
