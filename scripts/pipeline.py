#!/usr/bin/env python3
"""
PIPELINE de videos virales por nicho — end to end.
Uso:  python3 pipeline.py "<nicho>" [--platforms tiktok,youtube,instagram] [--per-platform 80] [--top 6]

Hace: scrape (Apify) -> filtro basura -> score viralidad -> gate calidad por
transcript (Supadata) -> escribe data/best.json + data/meta.json

Las capas de razonamiento (clasificar tipo/hook/idioma, generar ideas, análisis)
y la escritura a Notion las hace Claude en el skill, leyendo best.json.

Credenciales (en este orden de prioridad):
 1. variables de entorno  APIFY_TOKEN / SUPADATA_API_KEY
 2. ~/.videos-virales/config.json  {"apify_token": "...", "supadata_api_key": "..."}
 3. (legacy) ~/.apify/auth.json  /  ~/.supadata.json

Notas técnicas (lecciones horneadas — no cambiar sin razón):
 - TikTok: usar clockworks por HASHTAG (el keyword search de otros actores falla).
 - TikTok: NO usar filtro de fecha del actor (estrangula el resultado); filtrar en post.
 - Supadata: requiere User-Agent de navegador (banea urllib default -> 403).
"""
import json, os, sys, time, math, re, statistics, argparse, datetime as dt
import urllib.request, urllib.parse

# ---------------- credenciales ----------------
CONFIG_PATH = os.path.expanduser("~/.videos-virales/config.json")

def load_config():
    try:
        return json.load(open(CONFIG_PATH))
    except Exception:
        return {}

CFG = load_config()

def get_apify_token():
    if os.environ.get("APIFY_TOKEN"):
        return os.environ["APIFY_TOKEN"]
    if CFG.get("apify_token"):
        return CFG["apify_token"]
    try:
        return json.load(open(os.path.expanduser("~/.apify/auth.json")))["token"]
    except Exception:
        return None

def get_supadata_key():
    if os.environ.get("SUPADATA_API_KEY"):
        return os.environ["SUPADATA_API_KEY"]
    if CFG.get("supadata_api_key"):
        return CFG["supadata_api_key"]
    try:
        return json.load(open(os.path.expanduser("~/.supadata.json")))["api_key"]
    except Exception:
        return None

APIFY_TOKEN = get_apify_token()
SUPADATA_KEY = get_supadata_key()
if not APIFY_TOKEN:
    sys.exit("❌ Falta el token de Apify. Configúralo: export APIFY_TOKEN=... "
             "o crea ~/.videos-virales/config.json con {\"apify_token\":\"...\"}")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
NOW = dt.datetime.now(dt.timezone.utc)

ACTORS = {
    "tiktok":    "clockworks~tiktok-scraper",
    "youtube":   "streamers~youtube-scraper",
    "instagram": "apify~instagram-hashtag-scraper",
}

def actor_input(plat, niche, per_platform):
    if plat == "tiktok":   # por HASHTAG, sin filtro de fecha
        return {"hashtags": [niche.replace(" ", "")], "resultsPerPage": per_platform}
    if plat == "youtube":
        return {"searchQueries": [niche], "maxResults": per_platform,
                "sortingOrder": "views", "dateFilter": "month", "videoType": "video",
                "downloadSubtitles": False}
    if plat == "instagram":
        return {"hashtags": [niche.replace(" ", "")], "resultsType": "reels",
                "resultsLimit": per_platform}

# ---------------- apify ----------------
def api(method, path, body=None):
    url = f"https://api.apify.com/v2/{path}{'&' if '?' in path else '?'}token={APIFY_TOKEN}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)

def launch(plat, niche, per_platform):
    actor = ACTORS[plat]
    rid = api("POST", f"acts/{actor}/runs", actor_input(plat, niche, per_platform))["data"]["id"]
    print(f"  ▶ {plat}: run {rid}")
    return rid

def wait_all(runs, timeout=600):
    deadline = time.time() + timeout
    done = {}
    while runs and time.time() < deadline:
        for plat, rid in list(runs.items()):
            st = api("GET", f"actor-runs/{rid}")["data"]["status"]
            if st in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                done[plat] = (rid, st); runs.pop(plat)
                print(f"  ✓ {plat}: {st}")
        if runs: time.sleep(6)
    return done

def dataset(rid):
    return api("GET", f"actor-runs/{rid}/dataset/items?clean=true")

# ---------------- normalización ----------------
def age_days(iso):
    try:
        t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return max((NOW - t).total_seconds()/86400, 0.1)
    except Exception: return None

def parse_hms(s):
    if not s: return None
    p = [int(x) for x in str(s).split(":")]
    while len(p) < 3: p.insert(0, 0)
    return p[0]*3600 + p[1]*60 + p[2]

def norm(plat, it):
    if plat == "tiktok":
        return dict(platform="tiktok", id=str(it.get("id")), url=it.get("webVideoUrl"),
            author=(it.get("authorMeta") or {}).get("name"), caption=it.get("text") or "",
            hashtags=[h.get("name","").lower() for h in (it.get("hashtags") or [])],
            views=it.get("playCount") or 0, likes=it.get("diggCount") or 0,
            comments=it.get("commentCount") or 0, shares=it.get("shareCount") or 0,
            saves=it.get("collectCount") or 0, duration=(it.get("videoMeta") or {}).get("duration"),
            created=it.get("createTimeISO"), lang=it.get("textLanguage"),
            is_slideshow=bool(it.get("isSlideshow")), is_muted=bool(it.get("isMuted")),
            is_ad=bool(it.get("isAd") or it.get("isSponsored")))
    if plat == "youtube":
        return dict(platform="youtube", id=str(it.get("id")), url=it.get("url"),
            author=it.get("channelName"),
            caption=(it.get("title") or "") + " — " + (it.get("text") or "")[:300],
            hashtags=[h.lower().lstrip("#") for h in (it.get("hashtags") or [])],
            views=it.get("viewCount") or 0, likes=it.get("likes") or 0,
            comments=it.get("commentsCount") or 0, shares=0, saves=0,
            duration=parse_hms(it.get("duration")), created=it.get("date"), lang=None,
            is_slideshow=False, is_muted=False, is_ad=bool(it.get("isPaidContent")))
    if plat == "instagram":
        return dict(platform="instagram", id=str(it.get("id")), url=it.get("url"),
            author=it.get("ownerUsername"), caption=it.get("caption") or "",
            hashtags=[h.lower() for h in (it.get("hashtags") or [])],
            views=it.get("videoPlayCount") or it.get("igPlayCount") or 0,
            likes=it.get("likesCount") or 0, comments=it.get("commentsCount") or 0,
            shares=0, saves=0, duration=it.get("videoDuration"),
            created=it.get("timestamp"), lang=None,
            is_slideshow=(it.get("type") != "Video"), is_muted=False, is_ad=False)

MEME_MARKERS = {"meme","memes","funny","comedy","fail","lol","joke","prank","shitpost","ratio"}
MIN_DURATION, MAX_DURATION, MIN_VIEWS = 8, 3600, 1000

def quality_check(r):
    reasons = []
    if r["is_slideshow"]: reasons.append("slideshow/foto")
    if r["is_muted"]: reasons.append("muted")
    if r["is_ad"]: reasons.append("ad")
    d = r["duration"]
    if d is not None and d < MIN_DURATION: reasons.append("muy_corto")
    if d is not None and d > MAX_DURATION: reasons.append("muy_largo")
    if r["views"] < MIN_VIEWS: reasons.append("low_reach")
    cap_no_tags = re.sub(r"#\w+","",r["caption"]).strip()
    if not cap_no_tags and (MEME_MARKERS & set(r["hashtags"])):
        reasons.append("meme")
    return reasons

def zscores(vals):
    vals = [v for v in vals if v is not None]
    if len(vals) < 2: return lambda x: 0.0
    mu = statistics.mean(vals); sd = statistics.pstdev(vals) or 1.0
    return lambda x: (x-mu)/sd

# ---------------- supadata ----------------
def fetch_transcript(url):
    if not SUPADATA_KEY: return "__ERR__no_key"
    q = urllib.parse.urlencode({"url": url, "text": "true"})
    req = urllib.request.Request(f"https://api.supadata.ai/v1/transcript?{q}",
                                 headers={"x-api-key": SUPADATA_KEY, "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            d = json.load(r)
        c = d.get("content")
        if isinstance(c, str): return c
        if isinstance(c, list): return " ".join(s.get("text","") for s in c)
        return ""
    except urllib.error.HTTPError as e:
        return f"__ERR__{e.code}"
    except Exception as e:
        return f"__ERR__{e}"

MIN_WORDS, MIN_WPM = 25, 40

# ---------------- main ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("niche")
    ap.add_argument("--platforms", default="tiktok,youtube,instagram")
    ap.add_argument("--per-platform", type=int, default=80)
    ap.add_argument("--top", type=int, default=6, help="candidatos/plataforma al gate de transcript")
    ap.add_argument("--outdir", default="data")
    args = ap.parse_args()
    plats = [p.strip() for p in args.platforms.split(",") if p.strip()]
    OUT = args.outdir
    os.makedirs(OUT, exist_ok=True)

    print(f"🎯 nicho: {args.niche}  |  plataformas: {plats}")
    if not SUPADATA_KEY:
        print("⚠ Sin Supadata key: se omite el gate de transcript (se marcan todos sin verificar).")
    print("1) lanzando scrapers…")
    runs = {p: launch(p, args.niche, args.per_platform) for p in plats}
    done = wait_all(runs)

    print("2) descargando + normalizando…")
    rows = []
    for plat, (rid, st) in done.items():
        if st != "SUCCEEDED": print(f"  ⚠ {plat} {st}, skip"); continue
        items = dataset(rid)
        json.dump(items, open(f"{OUT}/{plat}_raw.json","w"), ensure_ascii=False)
        rows += [norm(plat, it) for it in items]
    print(f"   total scrapeado: {len(rows)}")

    print("3) filtro de basura + score de viralidad…")
    for r in rows:
        r["engagement"] = r["likes"]+r["comments"]+r["shares"]+r["saves"]
        r["eng_rate"] = r["engagement"]/r["views"] if r["views"] else 0
        ad = age_days(r["created"]); r["age_days"] = ad
        r["views_per_day"] = r["views"]/ad if ad else 0
        r["reject_reasons"] = quality_check(r)
        r["passed_prefilter"] = not r["reject_reasons"]
    for plat in plats:
        grp = [r for r in rows if r["platform"]==plat and r["passed_prefilter"]]
        if not grp: continue
        zv = zscores([math.log10(r["views"]+1) for r in grp])
        zd = zscores([math.log10(r["views_per_day"]+1) for r in grp])
        ze = zscores([r["eng_rate"] for r in grp])
        for r in grp:
            r["vir_score"] = round(0.35*zv(math.log10(r["views"]+1)) +
                                   0.30*zd(math.log10(r["views_per_day"]+1)) +
                                   0.35*ze(r["eng_rate"]), 3)
    passed = [r for r in rows if r["passed_prefilter"]]
    print(f"   pasaron pre-filtro: {len(passed)} / {len(rows)}")

    print("4) gate de calidad por transcript (Supadata)…")
    try: CACHE = json.load(open(f"{OUT}/transcripts.json"))
    except Exception: CACHE = {}
    best = []
    for plat in plats:
        cands = sorted([r for r in passed if r["platform"]==plat],
                       key=lambda r: r.get("vir_score",0), reverse=True)[:args.top]
        for r in cands:
            if SUPADATA_KEY:
                t = CACHE.get(r["url"]) or fetch_transcript(r["url"])
                if not t.startswith("__ERR__"): CACHE[r["url"]] = t
            else:
                t = "__ERR__no_key"
            words = re.findall(r"\w+", t.lower()) if not t.startswith("__ERR__") else []
            n = len(words)
            wpm = (n/(r["duration"]/60)) if r.get("duration") else None
            r["transcript"] = t[:4000] if not t.startswith("__ERR__") else ""
            r["transcript_words"] = n
            r["wpm"] = round(wpm,1) if wpm else None
            # sin key, dejamos pasar por score (Claude clasificará/limpia después)
            r["quality_pass"] = True if not SUPADATA_KEY else (n >= MIN_WORDS and (wpm is None or wpm >= MIN_WPM))
            if r["quality_pass"]: best.append(r)
    json.dump(CACHE, open(f"{OUT}/transcripts.json","w"), ensure_ascii=False)
    best.sort(key=lambda r: r["vir_score"], reverse=True)

    json.dump(rows, open(f"{OUT}/all_scored.json","w"), ensure_ascii=False, indent=1, default=str)
    json.dump(best, open(f"{OUT}/best.json","w"), ensure_ascii=False, indent=1, default=str)
    meta = dict(niche=args.niche, platforms=plats, scraped=len(rows),
                passed_prefilter=len(passed), quality_videos=len(best),
                run_date=NOW.date().isoformat())
    json.dump(meta, open(f"{OUT}/meta.json","w"), ensure_ascii=False, indent=1)
    print(f"\n✅ {len(best)} videos de CALIDAD -> {OUT}/best.json")
    print(f"   meta -> {OUT}/meta.json")

if __name__ == "__main__":
    main()
