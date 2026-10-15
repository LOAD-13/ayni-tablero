# Tablero de avance · Ayni Bank

Página con los KPIs del proyecto **AYNI** de Jira:
- story points por integrante frente a la cuota equitativa;
- burnup del proyecto y burndown por sprint;
- velocidad y avance por épica;
- un histórico diario de cuánto se avanzó en cada momento.

**Publicado en:** https://load-13.github.io/ayni-tablero/

## Cómo se actualiza

- **Cada día:** una GitHub Action (`.github/workflows/tablero.yml`) lee la API de Jira a las 06:00 de Lima, guarda la instantánea del día en `historico.json` y vuelve a publicar `docs/index.html`.
- **Cuando haga falta:** se puede lanzar a mano desde *Actions → Tablero → Run workflow*.

En local:

```bash
python generar.py            # necesita JIRA_TOKEN o el fichero ~/ayni-jira-token.txt
python generar.py --sin-red  # vuelve a pintar la página con el último docs/datos.json
```

Solo usa la biblioteca estándar de Python.

## Período evaluado

Solo se lee y se muestra lo del **Sprint 4 en adelante** (desde el 5-oct-2026), que es lo que revisa el docente. Se cambia con `TABLERO_DESDE_SPRINT` y `TABLERO_DESDE_FECHA`.

## Modo revisión (validar tareas)

Botón **Modo revisión** → usuario y contraseña del Scrum Master. La página solo guarda la huella SHA-256 de esas
credenciales, nunca la contraseña. Con la sesión abierta, cada tarea terminada tiene una casilla para marcarla como
validada.

Las marcas se guardan **en el navegador** de quien revisa. Para que una validación la vea todo el mundo, añade la
etiqueta `validada-sm` a la tarea en Jira: el tablero la lee en cada actualización.

## Reglas de lectura

- **Qué se cuenta.** Los story points son los de las **tareas hoja**: subtareas, y tareas o historias sin subtareas. Así nada se cuenta dos veces.
- **Integrantes sin cuenta en Jira.** Se asignan con la etiqueta `resp-<nombre>` (por ejemplo `resp-gerardo`).
- **Trabajo validado.** El Scrum Master añade la etiqueta `validada-sm` a una tarea terminada cuando revisó el trabajo.
- **Registros posteriores.** Lo que se terminó antes de registrarse en Jira lleva la etiqueta `registro-retroactivo`, y su fecha de vencimiento es la fecha real de entrega. El histórico usa esa fecha y no la del registro.
