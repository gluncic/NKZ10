from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Učitavanje zanimanja s opisima
with open("NKZ_descriptions_chatGPT4omini.json", encoding="utf-8") as f:
    zan_dict = json.load(f)

# Grupiranje po rodovima i skupinama
rodovi = {}
skupine = {}

for sifra, data in zan_dict.items():
    if "rod" not in data or "skupina" not in data:
        print(f"UPOZORENJE: zapis {sifra} nema rod ili skupinu")
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
    return templates.TemplateResponse("index.html", {"request": request, "rodovi": rodovi})

@app.get("/skupine/{rod}", response_class=HTMLResponse)
def prikazi_skupine(request: Request, rod: str):
    skupine_lista = sorted(list(rodovi.get(rod, [])))
    html = f"""
    <div id='rod-{rod}' class='blok'>
        <div class='rod' 
             hx-get='/sakrij-rod/{rod}' 
             hx-target='#rod-{rod}' 
             hx-swap='outerHTML'>
            {rod}
        </div>
    """
    for skupina in skupine_lista:
        html += f"""
        <div id='skupina-{skupina}' class='blok'>
            <div class='skupina' 
                 hx-get='/zanimanja/{skupina}' 
                 hx-target='#skupina-{skupina}' 
                 hx-swap='outerHTML'>
                {skupina}
            </div>
        </div>
        """
    html += "</div>"
    return html

@app.get("/sakrij-rod/{rod}", response_class=HTMLResponse)
def sakrij_rod(request: Request, rod: str):
    return f"""
    <div id='rod-{rod}' class='blok'>
        <div class='rod' 
             hx-get='/skupine/{rod}' 
             hx-target='#rod-{rod}' 
             hx-swap='outerHTML'>
            {rod}
        </div>
    </div>
    """

@app.get("/zanimanja/{skupina}", response_class=HTMLResponse)
def prikazi_zanimanja(request: Request, skupina: str):
    zanimanja = skupine.get(skupina, [])
    html = f"""
    <div id='skupina-{skupina}' class='blok'>
        <div class='skupina' 
             hx-get='/sakrij-skupinu/{skupina}' 
             hx-target='#skupina-{skupina}' 
             hx-swap='outerHTML'>
            {skupina}
        </div>
    """
    for z in zanimanja:
        html += f"""
        <div id='blok-{z['sifra']}' class='zanimanje-blok'>
            <div class='zanimanje'
                 hx-get='/toggle/{z['sifra']}'
                 hx-target='#blok-{z['sifra']}'
                 hx-swap='outerHTML'>
                {z['ime']}
            </div>
        </div>
        """
    html += "</div>"
    return html

@app.get("/sakrij-skupinu/{skupina}", response_class=HTMLResponse)
def sakrij_skupinu(request: Request, skupina: str):
    return f"""
    <div id='skupina-{skupina}' class='blok'>
        <div class='skupina' 
             hx-get='/zanimanja/{skupina}' 
             hx-target='#skupina-{skupina}' 
             hx-swap='outerHTML'>
            {skupina}
        </div>
    </div>
    """

@app.get("/toggle/{code}", response_class=HTMLResponse)
def toggle_opis(request: Request, code: str):
    opis = zan_dict[code]["description"]
    ime = zan_dict[code]["ime"]
    return f"""
    <div id='blok-{code}' class='zanimanje-blok'>
        <div class='zanimanje'
             hx-get='/sakrij/{code}'
             hx-target='#blok-{code}'
             hx-swap='outerHTML'>
            {ime}
        </div>
        <div class='opis'>{opis}</div>
    </div>
    """

@app.get("/sakrij/{code}", response_class=HTMLResponse)
def sakrij_opis(request: Request, code: str):
    ime = zan_dict[code]["ime"]
    return f"""
    <div id='blok-{code}' class='zanimanje-blok'>
        <div class='zanimanje'
             hx-get='/toggle/{code}'
             hx-target='#blok-{code}'
             hx-swap='outerHTML'>
            {ime}
        </div>
    </div>
    """
