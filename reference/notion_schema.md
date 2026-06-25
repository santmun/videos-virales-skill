# Esquemas de Notion (para crear las tablas en el setup)

En el primer uso, Claude crea estas 3 tablas en el Notion del usuario (bajo la página
padre que el usuario elija, o en la raíz del workspace) usando el MCP de Notion
(`notion-create-database`), y guarda los `data_source_id` resultantes con:

```
python3 scripts/vv_config.py set-notion --parent <PARENT_PAGE_ID> --lista <DS> --ideas <DS> --analisis <DS>
```

Crea **primero** la tabla Lista (las Ideas se relacionan a ella vía su `data_source_id`).

---

## 1) 📊 Lista de Videos con Data

```sql
CREATE TABLE (
"Video" TITLE,
"Plataforma" SELECT('tiktok':pink, 'youtube':red, 'instagram':purple),
"Nicho" RICH_TEXT,
"Autor" RICH_TEXT,
"URL" URL,
"Views" NUMBER,
"Likes" NUMBER,
"Comentarios" NUMBER,
"Engagement Rate" NUMBER FORMAT 'percent',
"Score Viralidad" NUMBER COMMENT 'z-score normalizado por plataforma',
"Duracion (s)" NUMBER,
"WPM" NUMBER COMMENT 'palabras por minuto del transcript',
"Dias" NUMBER COMMENT 'antiguedad en dias',
"Tipo Contenido" SELECT('educativo':blue, 'storytelling':orange, 'promo':gray, 'reto/demo':green, 'motivacional':yellow, 'musica/baile':pink),
"Idioma" RICH_TEXT,
"Hook" RICH_TEXT COMMENT 'gancho de los primeros segundos',
"Transcript" RICH_TEXT,
"Fecha Scrape" DATE
)
```

## 2) 💡 Ideas de Videos
La columna `Basado en` es una RELATION al `data_source_id` de la tabla Lista (sustituir `<LISTA_DS>`).

```sql
CREATE TABLE (
"Idea" TITLE,
"Nicho Destino" RICH_TEXT,
"Formato" SELECT('short/reel':pink, 'youtube largo':red, 'tiktok':purple),
"Hook Propuesto" RICH_TEXT,
"Angulo" RICH_TEXT COMMENT 'el angulo o giro de la idea',
"Por que funciona" RICH_TEXT,
"Basado en" RELATION('<LISTA_DS>', DUAL 'Ideas derivadas'),
"Estado" SELECT('idea':gray, 'en produccion':yellow, 'publicado':green),
"Fecha" DATE
)
```

## 3) 🧠 Análisis

```sql
CREATE TABLE (
"Analisis" TITLE,
"Nicho" RICH_TEXT,
"Fecha" DATE,
"Videos Analizados" NUMBER,
"Plataformas" MULTI_SELECT('tiktok':pink, 'youtube':red, 'instagram':purple),
"Hooks Comunes" RICH_TEXT,
"Formatos que Funcionan" RICH_TEXT,
"Patrones Clave" RICH_TEXT,
"Insights y Recomendaciones" RICH_TEXT,
"Oportunidad de Adaptacion" RICH_TEXT COMMENT 'como adaptar estos virales a otro nicho'
)
```

---

## Notas para escribir filas (create-pages)
- Parent: `{type:"data_source_id", data_source_id:"<DS>"}`.
- La columna URL se referencia como `userDefined:URL` en las propiedades.
- Las fechas usan la forma expandida: `date:Fecha Scrape:start`, `date:Fecha:start`.
- `Engagement Rate` se guarda como fracción 0–1 (ej. 0.229 = 22.9%).
- `Basado en` (relación) se pasa como string JSON array de URLs de página: `["https://www.notion.so/<page_id_sin_guiones>"]`.
- `Plataformas` (multi-select) se pasa como string JSON array: `["tiktok","youtube"]`.
