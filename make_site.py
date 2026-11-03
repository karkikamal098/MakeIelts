"""Build the production page (index.html) and the private preview (makeielts.html) from site_src.html."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, "tests", "build")
slugs = sys.argv[1:] or ["t01"]
src = open(os.path.join(HERE, "site_src.html")).read()
tests, keys = [], {}
for slug in slugs:
    pub = json.load(open(f"{B}/{slug}.public.json")); key = json.load(open(f"{B}/{slug}.key.json"))
    meta_p = f"{B}/audio/{slug}/meta.json"
    if os.path.exists(meta_p):
        for p, m in zip(pub["listening"]["parts"], json.load(open(meta_p))): p["dur"], p["marks"] = m["dur"], m["marks"]
    json.dump(pub, open(f"{B}/{slug}.public.final.json", "w"), ensure_ascii=False, separators=(",", ":"))
    tests.append(pub); keys[slug] = key
head = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>'
open(os.path.join(HERE, "index.html"), "w").write(head + src + "</body></html>")
local = "<script>window.__LOCAL=" + json.dumps({"tests": tests, "keys": keys, "unlockAll": True}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";</script>\n"
i = src.index("<script>")
prev = src[:i] + local + src[i:]
open(os.path.join(HERE, "makeielts.html"), "w").write(prev)
open(os.path.join(HERE, "preview_test.html"), "w").write(head + prev + "</body></html>")
print("built", slugs, "index.html", os.path.getsize("index.html"), "makeielts.html", os.path.getsize("makeielts.html"))
