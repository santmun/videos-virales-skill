#!/usr/bin/env python3
"""
Maneja la configuración del skill videos-virales en ~/.videos-virales/config.json
(permisos 600). Las llaves se pasan por VARIABLE DE ENTORNO para no exponerlas en
el historial de la shell.

Comandos:
  python3 vv_config.py show        # estado actual (llaves enmascaradas)
  python3 vv_config.py check       # valida Apify + Supadata contra sus APIs
  APIFY_TOKEN=.. SUPADATA_API_KEY=.. python3 vv_config.py set-keys
  python3 vv_config.py set-notion --parent <id> --lista <ds> --ideas <ds> --analisis <ds>
"""
import json, os, sys, urllib.request, argparse

DIR = os.path.expanduser("~/.videos-virales")
PATH = os.path.join(DIR, "config.json")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

def load():
    try: return json.load(open(PATH))
    except Exception: return {}

def save(cfg):
    os.makedirs(DIR, exist_ok=True)
    json.dump(cfg, open(PATH, "w"), indent=2, ensure_ascii=False)
    os.chmod(PATH, 0o600)

def mask(s):
    if not s: return "(falta)"
    return s[:4] + "…" + s[-4:] if len(s) > 10 else "••••"

def cmd_show():
    cfg = load()
    n = cfg.get("notion", {})
    print(f"config: {PATH}")
    print(f"  apify_token:      {mask(cfg.get('apify_token'))}")
    print(f"  supadata_api_key: {mask(cfg.get('supadata_api_key'))}")
    print(f"  notion.parent:    {n.get('parent_page_id','(falta)')}")
    print(f"  notion.lista:     {n.get('lista_ds','(falta)')}")
    print(f"  notion.ideas:     {n.get('ideas_ds','(falta)')}")
    print(f"  notion.analisis:  {n.get('analisis_ds','(falta)')}")
    ready = bool(cfg.get('apify_token') and n.get('lista_ds') and n.get('ideas_ds') and n.get('analisis_ds'))
    print(f"  LISTO PARA CORRER: {'sí' if ready else 'no — falta setup'}")

def cmd_set_keys():
    cfg = load()
    apify = os.environ.get("APIFY_TOKEN")
    supa = os.environ.get("SUPADATA_API_KEY")
    if apify: cfg["apify_token"] = apify.strip()
    if supa: cfg["supadata_api_key"] = supa.strip()
    save(cfg)
    print("✓ llaves guardadas en", PATH)
    if not apify: print("  (no se pasó APIFY_TOKEN)")
    if not supa: print("  (no se pasó SUPADATA_API_KEY)")

def cmd_set_notion(a):
    cfg = load()
    n = cfg.setdefault("notion", {})
    if a.parent: n["parent_page_id"] = a.parent
    if a.lista: n["lista_ds"] = a.lista
    if a.ideas: n["ideas_ds"] = a.ideas
    if a.analisis: n["analisis_ds"] = a.analisis
    save(cfg)
    print("✓ data sources de Notion guardados en", PATH)

def cmd_check():
    cfg = load()
    ok = True
    # Apify
    t = os.environ.get("APIFY_TOKEN") or cfg.get("apify_token")
    if not t:
        print("✗ Apify: sin token"); ok = False
    else:
        try:
            req = urllib.request.Request(f"https://api.apify.com/v2/users/me?token={t}")
            with urllib.request.urlopen(req, timeout=20) as r:
                u = json.load(r)["data"]
            print(f"✓ Apify OK — usuario: {u.get('username')}")
        except Exception as e:
            print(f"✗ Apify token inválido: {e}"); ok = False
    # Supadata
    k = os.environ.get("SUPADATA_API_KEY") or cfg.get("supadata_api_key")
    if not k:
        print("• Supadata: sin key (opcional, pero recomendada para el filtro de calidad)")
    else:
        try:
            url = "https://api.supadata.ai/v1/transcript?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&text=true"
            req = urllib.request.Request(url, headers={"x-api-key": k, "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                json.load(r)
            print("✓ Supadata OK")
        except urllib.error.HTTPError as e:
            if e.code in (402, 429):
                print(f"✓ Supadata key válida (HTTP {e.code}: límite/crédito, pero autentica)")
            else:
                print(f"✗ Supadata key inválida (HTTP {e.code})"); ok = False
        except Exception as e:
            print(f"✗ Supadata error: {e}"); ok = False
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show"); sub.add_parser("check"); sub.add_parser("set-keys")
    sn = sub.add_parser("set-notion")
    sn.add_argument("--parent"); sn.add_argument("--lista")
    sn.add_argument("--ideas"); sn.add_argument("--analisis")
    a = ap.parse_args()
    if a.cmd == "show": cmd_show()
    elif a.cmd == "check": cmd_check()
    elif a.cmd == "set-keys": cmd_set_keys()
    elif a.cmd == "set-notion": cmd_set_notion(a)
