# 🔥 Videos Virales — Skill para Claude Code

Un **skill de Claude Code** que busca los videos **virales** de cualquier nicho en **TikTok + YouTube + Instagram**, filtra la basura (memes, audio-only, música, ads), lee los **transcripts** para quedarse solo con contenido de sustancia, y arma **3 tablas en tu Notion**:

- 📊 **Lista de Videos con Data** — cada viral con sus métricas, score de viralidad y transcript
- 💡 **Ideas de Videos** — ideas para tu canal, adaptando los formatos ganadores a tu nicho
- 🧠 **Análisis** — patrones, hooks y formatos que funcionan, con recomendaciones

Tú solo dices: **"busca videos virales de cocina"** y hace todo solo.

---

## ⚙️ Cómo funciona (por dentro)

```
nicho → scrape 3 plataformas (Apify) → filtro de basura → score de viralidad
      → transcripts (Supadata) → clasificación con IA → 3 tablas en Notion
```

- **Apify** corre los scrapers (pago por uso, centavos por corrida).
- **Supadata** saca los transcripts para distinguir contenido real de música/relleno.
- **Notion MCP** escribe las tablas en tu workspace.
- **Claude** clasifica, genera ideas y sintetiza el análisis.

Costo típico por corrida: **< $0.50 USD** (Apify + Supadata).

---

## 📦 Instalación (con Claude Code)

La forma más fácil: **pásale este enlace a Claude Code y pídele que lo instale.**

> Instala este skill: https://github.com/santmun/videos-virales-skill

Claude lo clonará en `~/.claude/skills/videos-virales`. Si prefieres a mano:

```bash
git clone https://github.com/santmun/videos-virales-skill ~/.claude/skills/videos-virales
```

Reinicia Claude Code (o abre una sesión nueva) para que detecte el skill.

---

## 🔑 Configuración (primera vez)

La primera vez que lo uses, el skill te va a pedir tus llaves. Necesitas:

### 1. Apify (obligatoria)
1. Crea cuenta en **https://console.apify.com/** (el plan gratis trae crédito mensual).
2. Ve a **Settings → API & Integrations**.
3. Copia tu **Personal API token**.

### 2. Supadata (recomendada)
1. Regístrate en **https://supadata.ai/** (tiene tier gratis).
2. En el Dashboard, ve a **API Keys** y copia tu key.
3. Sirve para leer transcripts y filtrar la música/relleno. Si no la pones, el skill corre igual pero con más ruido.

### 3. Notion
Necesitas el **conector de Notion activado** en Claude Code (*Settings → Connectors → Notion*). El skill crea las 3 tablas solo, la primera vez, en la página que le indiques.

> Claude guarda tus llaves en `~/.videos-virales/config.json` (permisos 600, solo tú). **Nunca se suben a ningún lado.**

---

## 🚀 Uso

```
busca videos virales de finanzas personales
```
```
analiza el nicho de skincare y dame ideas para mi canal
```
```
/videos-virales recetas veganas
```

El skill scrapea, filtra, puntúa, clasifica y te llena las 3 tablas de Notion. Al final te da un resumen con el top 3 y los links.

### Opciones
- Más cobertura: corre más videos por plataforma (más costo).
- Nichos de varias palabras: usa un término enfocado como hashtag (ej. "claude code" en vez de "AI agents and claude code").

---

## 🧠 ¿Por qué es bueno?

- **No es solo scraping**: distingue viralidad real (alcance + velocidad + engagement, normalizado por plataforma) y descarta lo que infla números sin sustancia.
- **Filtra música y relleno** leyendo el transcript, no solo metadata.
- **Te da ideas accionables**: toma los formatos que ya funcionan y los traduce a tu nicho/idioma.
- **Todo queda en Notion**, listo para planear contenido.

---

## 🛠️ Requisitos
- Claude Code
- Python 3 (viene en macOS/Linux)
- Cuenta de Apify (gratis) · Supadata (gratis, opcional) · Notion (conector en Claude Code)

## 📄 Licencia
MIT — úsalo, modifícalo, compártelo.

---

Hecho con ❤️ para la comunidad de [Horizontes IA](https://horizontesia.com).
