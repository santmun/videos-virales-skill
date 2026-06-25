---
name: videos-virales
description: Busca y analiza los videos VIRALES de un nicho en TikTok + YouTube + Instagram (vía Apify), filtra la basura (memes, audio-only, slideshows, música/lyrics, ads), lee transcripts con Supadata, y escribe 3 tablas en Notion — Lista de Videos con Data, Ideas de Videos (adaptadas a otro nicho) y Análisis. Úsalo cuando el usuario diga "busca videos virales de <nicho>", "qué se está volviendo viral en <nicho>", "tráeme los mejores videos de <nicho>", "analiza el nicho de <X>", "ideas de video de <nicho>", o invoque /videos-virales. Acepta el nicho y opcionalmente un nicho destino para adaptar las ideas.
---

# Videos Virales por Nicho

Pipeline autónomo: **scrape multi-plataforma → filtro de calidad → score de viralidad → gate por transcript → 3 tablas en Notion**. El usuario solo da el nicho.

`{baseDir}` = la carpeta de este skill (`~/.claude/skills/videos-virales`).

## Cuándo se activa
Triggers: "busca videos virales de <nicho>", "qué está pegando en <nicho>", "tráeme lo mejor de <nicho>", "analiza el nicho <X>", "/videos-virales <nicho>". Si no hay nicho, pregúntalo. El **nicho destino** para las ideas es opcional (default: el mismo nicho).

---

## PASO 0 — Setup (verificar SIEMPRE antes de correr)

Corre el chequeo de configuración:
```bash
python3 {baseDir}/scripts/vv_config.py show
```

### 0a. Si faltan las API keys (`apify_token` o `supadata_api_key`)
Pídeselas al usuario explicándole cómo obtenerlas (NO las inventes ni las pongas en el historial):

- **Apify** (obligatoria): https://console.apify.com/ → Settings → API & Integrations → copiar el **Personal API token**. Plan gratis trae crédito mensual suficiente para varias corridas.
- **Supadata** (recomendada, para el filtro de calidad por transcript): https://supadata.ai/ → registrarse → Dashboard → API Keys. Hay tier gratis. Si el usuario no la quiere, el skill corre igual pero sin el gate de transcripts (saldrá más ruido).

Guárdalas pasándolas por **variable de entorno** (no como argumento) para no exponerlas:
```bash
APIFY_TOKEN="<token>" SUPADATA_API_KEY="<key>" python3 {baseDir}/scripts/vv_config.py set-keys
python3 {baseDir}/scripts/vv_config.py check   # valida contra las APIs
```

### 0b. Si faltan los data sources de Notion (`notion.lista_ds`, etc.)
Hay que crear las 3 tablas en el Notion del usuario (una sola vez). Requiere el **MCP de Notion conectado** en Claude Code. Si no está, dile al usuario que lo conecte (Settings → Connectors → Notion) y detente.

1. Pregunta al usuario bajo qué página de Notion quiere las tablas (o créalas en la raíz del workspace). Opcional: crea una página madre "🔥 Scraper de Videos Virales" con `notion-create-pages` y usa su id.
2. Lee los 3 esquemas en `{baseDir}/reference/notion_schema.md` y crea las tablas con `notion-create-database` **en este orden**: Lista → (toma su `data_source_id`) → Ideas (mete ese id en la RELATION `Basado en`, sustituyendo `<LISTA_DS>`) → Análisis.
3. Guarda los ids:
```bash
python3 {baseDir}/scripts/vv_config.py set-notion --parent <PARENT_ID> --lista <LISTA_DS> --ideas <IDEAS_DS> --analisis <ANALISIS_DS>
```

Cuando `vv_config.py show` diga `LISTO PARA CORRER: sí`, continúa.

---

## PASO 1 — Scrape + filtro + score + transcripts (lo hace el script)
```bash
cd {baseDir}/scripts
python3 pipeline.py "<nicho>" --per-platform 80 --top 6
```
Produce en `{baseDir}/scripts/data/`: `best.json` (videos que pasaron el gate, con métricas + transcript), `all_scored.json` (todo) y `meta.json` (resumen). Reporta al usuario los números de `meta.json`.

**Nichos de varias palabras**: el término se usa como hashtag en TikTok/IG (sin espacios). Si el nicho es una frase larga o lleva "and/y", elige con el usuario un término/hashtag enfocado (ej. de "AI agents and claude code" → usa "claude code" o corre dos pasadas). El nicho completo sí sirve como búsqueda en YouTube.

## PASO 2 — Clasificación (la haces TÚ, Claude, leyendo `best.json`)
Para cada video: lee `transcript` + `caption` y determina:
- **Tipo Contenido**: `educativo | storytelling | promo | reto/demo | motivacional | musica/baile`.
- **Hook**: el gancho real de los primeros segundos, 1 frase clara.
- **Idioma**: ISO (`en`, `es`, `pt`, …).

**REGLA DE CALIDAD CRÍTICA**: el gate por wpm deja pasar **lyrics/música** (un rap a buen wpm parece habla). Si el transcript es letra de canción / sin contenido informativo o narrativo, clasifícalo `musica/baile`, antepón `[FILTRADO]` al Hook, y por default **NO lo subas** a la Lista (salvo que el usuario pida ver todo).

## PASO 3 — Escribir **Lista de Videos con Data**
`notion-create-pages` con `parent: {data_source_id: "<lista_ds de config>"}`. Una página por video (excluyendo música). Propiedades (nombres exactos):
`Video` (title, ≤80 chars), `Plataforma` (select), `Nicho` (texto), `Autor`, `userDefined:URL`, `Views`, `Likes`, `Comentarios`, `Engagement Rate` (fracción 0–1), `Score Viralidad`, `Duracion (s)`, `WPM`, `Dias`, `Tipo Contenido` (select), `Idioma`, `Hook`, `Transcript` (≤1200 chars), `date:Fecha Scrape:start` (hoy).
Guarda los `page.id` que devuelve (para la relación del paso 4).

## PASO 4 — Generar y escribir **Ideas de Videos**
Identifica los hooks/formatos ganadores y genera 4–6 ideas que TRASLADAN esas mecánicas al **nicho destino** (default: el mismo nicho, tropicalizado al idioma/marca del usuario). `notion-create-pages` con `parent: {data_source_id: "<ideas_ds>"}`:
`Idea` (title), `Nicho Destino` (texto), `Formato` (select), `Hook Propuesto`, `Angulo` (qué formato viral imita), `Por que funciona` (cita la métrica del original), `Basado en` (JSON array string con la URL de la página del video fuente del paso 3), `Estado`=`idea`, `date:Fecha:start`.

## PASO 5 — Escribir **Análisis** (1 registro por corrida)
`notion-create-pages` con `parent: {data_source_id: "<analisis_ds>"}`:
`Analisis` (title, "<Nicho> — <fecha>"), `Nicho` (texto), `date:Fecha:start`, `Videos Analizados`, `Plataformas` (JSON array), `Hooks Comunes`, `Formatos que Funcionan`, `Patrones Clave`, `Insights y Recomendaciones` (accionable), `Oportunidad de Adaptacion`.

## PASO 6 — Reportar
Resumen corto: # scrapeados → # filtrados → # de calidad, top 3 con su score, y los links a las 3 tablas. Menciona el costo aprox (Apify+Supadata suele ser < $0.50/corrida).

---

## Notas técnicas (lecciones horneadas — no repetir errores)
- **TikTok**: `clockworks/tiktok-scraper` por **hashtag**. NO usar keyword search (otros actores fallan con error C098). NO usar el filtro de fecha del actor (estrangula a 1 resultado); filtrar fecha en post-proceso.
- **YouTube**: `streamers/youtube-scraper`, `searchQueries` + `sortingOrder: views` + `dateFilter: month`.
- **Instagram**: `apify/instagram-hashtag-scraper`, `resultsType: reels`.
- **Supadata**: requiere `User-Agent` de navegador (banea urllib default → 403). Caché en `data/transcripts.json`.
- **Score de viralidad**: z-score por plataforma = 0.35·log(views) + 0.30·log(views/día) + 0.35·engagement_rate. NO comparar views crudos entre plataformas.
- **Notion**: columnas de nicho = texto libre (cualquier nicho). `Plataforma`/`Tipo Contenido`/`Formato`/`Estado` son SELECT de opciones fijas. Fechas: forma expandida `date:<Columna>:start`.

## Parámetros del script
`python3 pipeline.py "<nicho>" [--platforms tiktok,youtube,instagram] [--per-platform 80] [--top 6]`
