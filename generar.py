# -*- coding: utf-8 -*-
"""Genera el tablero de avance de Ayni Bank a partir de la API de Jira.

    python generar.py            → lee Jira, actualiza historico.json y escribe docs/index.html
    python generar.py --sin-red  → regenera la página con el último datos.json (para probar el diseño)

El token se lee de la variable JIRA_TOKEN o del fichero ~/.ayni-jira-token. Solo usa la biblioteca
estándar de Python.
"""
import base64, datetime as dt, json, os, pathlib, sys, urllib.request, urllib.error

SITIO = os.environ.get("JIRA_SITIO", "https://jloadenegri.atlassian.net")
CORREO = os.environ.get("JIRA_CORREO", "jloadenegri@gmail.com")
PROYECTO = "AYNI"
SP, SPRINT = "customfield_10016", "customfield_10020"
RAIZ = pathlib.Path(__file__).parent
LIMA = dt.timezone(dt.timedelta(hours=-5))

# Quien todavía no tiene cuenta en Jira se marca con una etiqueta resp-<nombre>
SIN_CUENTA = {"resp-gerardo": "Gerardo Socualaya Mandamiento"}
NOMBRES = {  # nombre visible en Jira → nombre del equipo
    "Joaquín Loa Denegri": "Joaquín Loa Denegri",
    "Kiara Santti": "Kiara Santti Saavedra",
    "Eduardo Vargas Zumaeta (EduardoVaZu)": "Eduardo Vargas Zumaeta",
    "Frank": "Frank Sotomayor Suasnabar",
    "fabian.gar.0405": "Fabián García Champi",
}
EQUIPO = ["Joaquín Loa Denegri", "Kiara Santti Saavedra", "Eduardo Vargas Zumaeta",
          "Frank Sotomayor Suasnabar", "Fabián García Champi", "Gerardo Socualaya Mandamiento"]


def token():
    t = os.environ.get("JIRA_TOKEN")
    if not t:
        f = pathlib.Path.home() / ".ayni-jira-token"
        t = f.read_text(encoding="utf-8").strip() if f.exists() else ""
    if not t:
        sys.exit("Falta el token de Jira (JIRA_TOKEN o ~/.ayni-jira-token)")
    return t


def jira(ruta, cuerpo=None):
    auth = base64.b64encode(f"{CORREO}:{token()}".encode()).decode()
    req = urllib.request.Request(SITIO + ruta, data=json.dumps(cuerpo).encode() if cuerpo else None,
                                 method="POST" if cuerpo else "GET",
                                 headers={"Authorization": "Basic " + auth, "Accept": "application/json",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"Jira respondió {e.code} en {ruta}: {e.read().decode()[:300]}")


def leer_incidencias():
    campos = ["summary", "status", "issuetype", "assignee", SP, SPRINT, "parent", "labels", "duedate",
              "created", "statuscategorychangedate", "resolutiondate"]
    salida, pagina = [], None
    while True:
        cuerpo = {"jql": f"project = {PROYECTO} ORDER BY key", "fields": campos, "maxResults": 100}
        if pagina:
            cuerpo["nextPageToken"] = pagina
        r = jira("/rest/api/3/search/jql", cuerpo)
        salida += r["issues"]
        pagina = r.get("nextPageToken")
        if not pagina:
            return salida


def dia(iso):
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(LIMA).date().isoformat() if iso else None


def normalizar(crudas):
    """Una fila por incidencia, con su sprint (las subtareas heredan el de su padre) y su responsable."""
    por_clave = {i["key"]: i for i in crudas}
    sprints = {}
    filas = []
    for i in crudas:
        f = i["fields"]
        for s in f.get(SPRINT) or []:
            sprints[s["id"]] = {"id": s["id"], "nombre": s["name"], "estado": s["state"],
                                "inicio": dia(s.get("startDate")), "fin": dia(s.get("endDate"))}
    hijos = {}
    for i in crudas:
        p = (i["fields"].get("parent") or {}).get("key")
        if p and i["fields"]["issuetype"]["subtask"]:
            hijos.setdefault(p, []).append(i["key"])
    for i in crudas:
        f = i["fields"]
        tipo = f["issuetype"]["name"]
        sprint_de = f
        if f["issuetype"]["subtask"] and f.get("parent"):
            sprint_de = por_clave.get(f["parent"]["key"], {}).get("fields", {})
        lista = sprint_de.get(SPRINT) or []
        sprint = max(lista, key=lambda s: s["id"])["id"] if lista else None
        etiquetas = f.get("labels") or []
        resp = NOMBRES.get((f.get("assignee") or {}).get("displayName"), (f.get("assignee") or {}).get("displayName"))
        for et, nombre in SIN_CUENTA.items():
            if et in etiquetas:
                resp = nombre
        cat = f["status"]["statusCategory"]["key"]  # new | indeterminate | done
        hecho_en = None
        if cat == "done":
            hecho_en = f.get("duedate") if "registro-retroactivo" in etiquetas and f.get("duedate") \
                else dia(f.get("resolutiondate") or f.get("statuscategorychangedate"))
        padre = (f.get("parent") or {}).get("key")
        epica = padre if padre and por_clave.get(padre, {}).get("fields", {}).get("issuetype", {}).get("name") == "Epic" else None
        if f["issuetype"]["subtask"] and padre:
            pp = (por_clave.get(padre, {}).get("fields", {}).get("parent") or {}).get("key")
            epica = pp
        filas.append({
            "clave": i["key"], "resumen": f["summary"], "tipo": tipo, "estado": f["status"]["name"], "cat": cat,
            "sp": f.get(SP) or 0, "sprint": sprint, "resp": resp or "Sin asignar", "padre": padre, "epica": epica,
            "hoja": tipo != "Epic" and i["key"] not in hijos, "creado": dia(f["created"]), "hecho": hecho_en,
            "validada": "validada-sm" in etiquetas, "etiquetas": etiquetas,
        })
    epicas = {i["key"]: i["fields"]["summary"] for i in crudas if i["fields"]["issuetype"]["name"] == "Epic"}
    return filas, sorted(sprints.values(), key=lambda s: s["id"]), epicas


def instantanea(filas):
    hojas = [f for f in filas if f["hoja"]]
    por = {p: {"hecho": 0, "total": 0} for p in EQUIPO}
    for f in hojas:
        if f["resp"] in por:
            por[f["resp"]]["total"] += f["sp"]
            if f["cat"] == "done":
                por[f["resp"]]["hecho"] += f["sp"]
    return {"fecha": dt.datetime.now(LIMA).date().isoformat(),
            "sp_total": sum(f["sp"] for f in hojas), "sp_hecho": sum(f["sp"] for f in hojas if f["cat"] == "done"),
            "abiertas": sum(1 for f in filas if f["cat"] != "done" and f["tipo"] != "Epic"), "por_persona": por}


def main():
    datos_f = RAIZ / "docs" / "datos.json"
    if "--sin-red" in sys.argv:
        datos = json.loads(datos_f.read_text(encoding="utf-8"))
    else:
        filas, sprints, epicas = normalizar(leer_incidencias())
        hist_f = RAIZ / "historico.json"
        historico = json.loads(hist_f.read_text(encoding="utf-8")) if hist_f.exists() else []
        hoy = instantanea(filas)
        historico = [h for h in historico if h["fecha"] != hoy["fecha"]] + [hoy]
        hist_f.write_text(json.dumps(historico, ensure_ascii=False, indent=1), encoding="utf-8")
        datos = {"generado": dt.datetime.now(LIMA).strftime("%Y-%m-%d %H:%M"), "sitio": SITIO, "proyecto": PROYECTO,
                 "equipo": EQUIPO, "filas": filas, "sprints": sprints, "epicas": epicas, "historico": historico}
        datos_f.parent.mkdir(exist_ok=True)
        datos_f.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    plantilla = (RAIZ / "plantilla.html").read_text(encoding="utf-8")
    pagina = plantilla.replace("/*__DATOS__*/null", json.dumps(datos, ensure_ascii=False).replace("</", "<\\/"))
    (RAIZ / "docs" / "index.html").write_text(pagina, encoding="utf-8")
    print(f"Tablero generado: {len(datos['filas'])} incidencias · {datos['generado']}")


if __name__ == "__main__":
    main()
