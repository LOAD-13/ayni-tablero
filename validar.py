# -*- coding: utf-8 -*-
"""Marca (o desmarca) tareas terminadas como validadas por el Scrum Master: etiqueta validada-sm en Jira.

    CLAVES="AYNI-12,AYNI-40" ACCION=validar python validar.py

Lo lanza el workflow «Validar» desde el modo de revisión del tablero. Solo toca esa etiqueta y solo en
incidencias del proyecto AYNI que estén terminadas.
"""
import os, re, sys
import generar

ETIQUETA = "validada-sm"


def main():
    accion = os.environ.get("ACCION", "")
    claves = [c.strip().upper() for c in os.environ.get("CLAVES", "").split(",") if c.strip()]
    if accion not in ("validar", "quitar"):
        sys.exit("ACCION debe ser validar o quitar")
    if not claves or len(claves) > 60 or not all(re.fullmatch(r"AYNI-\d{1,5}", c) for c in claves):
        sys.exit("CLAVES debe ser una lista de 1 a 60 claves AYNI-NNN separadas por comas")
    for clave in claves:
        f = generar.jira(f"/rest/api/3/issue/{clave}?fields=status,labels,project")["fields"]
        if f["project"]["key"] != generar.PROYECTO:
            sys.exit(f"{clave} no es del proyecto {generar.PROYECTO}")
        if accion == "validar" and f["status"]["statusCategory"]["key"] != "done":
            print(f"{clave}: no está terminada, se omite")
            continue
        op = "add" if accion == "validar" else "remove"
        generar.jira_put(f"/rest/api/3/issue/{clave}", {"update": {"labels": [{op: ETIQUETA}]}})
        print(f"{clave}: {accion}")


if __name__ == "__main__":
    main()
