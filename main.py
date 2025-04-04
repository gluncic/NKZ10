# Endpoint za prikaz skupina (druga razina)
@app.get("/skupine/{rod_slug}", response_class=HTMLResponse)
def skupine_rod(request: Request, rod_slug: str):
    rod = get_rod_by_slug(rod_slug)
    if not rod:
        raise HTTPException(status_code=404, detail="Rod nije pronađen")
    skupine_lista = sorted(list(rodovi.get(rod, [])))
    html = f"<div class='blok' id='rod-{rod_slug}'>"
    # Link za rod (prva razina) s klasom 'rod-link'
    html += f'<a class="rod-link" href="#" hx-get="/sakrij-rod/{rod_slug}" hx-target="#rod-{rod_slug}" hx-swap="outerHTML">{rod}</a>'
    html += "<ul>"
    for skupina in skupine_lista:
        skupina_slug = slugify(skupina)
        html += f'<li><div id="skupina-{skupina_slug}">'
        # Link za skupinu (druga razina) s klasom 'skupina-link'
        html += f'<a class="skupina-link" href="#" hx-get="/zanimanja/{skupina_slug}" hx-target="#skupina-{skupina_slug}" hx-swap="outerHTML">{skupina}</a>'
        html += "</div></li>"
    html += "</ul></div>"
    return html

# Endpoint za prikaz zanimanja (treća razina)
@app.get("/zanimanja/{skupina_slug}", response_class=HTMLResponse)
def zanimanja_skupina(request: Request, skupina_slug: str):
    skupina = get_skupina_by_slug(skupina_slug)
    if not skupina:
        raise HTTPException(status_code=404, detail="Skupina nije pronađena")
    zanimanja = skupine.get(skupina, [])
    html = f"<div class='blok' id='skupina-{skupina_slug}'>"
    # Link za skupinu s klasom 'skupina-link'
    html += f'<a class="skupina-link" href="#" hx-get="/sakrij-skupinu/{skupina_slug}" hx-target="#skupina-{skupina_slug}" hx-swap="outerHTML">{skupina}</a>'
    html += "<ul>"
    for z in zanimanja:
        sifra = z["sifra"]
        ime = z["ime"]
        # Omotavamo link u div s id "blok-<sifra>" i klasom 'zanimanje-div'
        html += f'<li><div id="blok-{sifra}" class="zanimanje-div">'
        # Link za zanimanje (treća razina) s klasom 'zanimanje-link'
        html += f'<a class="zanimanje-link" href="#" hx-get="/toggle/{sifra}" hx-target="#blok-{sifra}" hx-swap="outerHTML">{ime}</a>'
        html += "</div></li>"
    html += "</ul></div>"
    return html
