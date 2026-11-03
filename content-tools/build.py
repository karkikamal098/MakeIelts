"""Validate a test, split public data from answer keys, and write JSON.
Usage: python3 build.py t01 [t02 ...]"""
import importlib, json, re, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "build")
os.makedirs(OUT, exist_ok=True)
KEY_FIELDS = {"answer", "accept", "traps", "distract", "def", "evidence", "why", "para"}
TRAPS = {"ng_vs_false", "word_match", "assumption", "paraphrase_miss", "contradiction_miss", "word_limit", "spelling", "plural",
         "correction", "list_distractor", "considered_rejected", "lost_track", "unanswered"}
PARAS = None
FIXED = {"tfng": ["TRUE", "FALSE", "NOT GIVEN"], "ynng": ["YES", "NO", "NOT GIVEN"]}

def norm(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().lower()

def check_evidence(ev, corpus, where, errs):
    for frag in [f.strip(" .,…") for f in re.split(r"…|\.\.\. | — ", ev)]:
        if len(frag) < 6: continue
        if norm(frag) not in corpus: errs.append(f"{where}: evidence not found: «{frag[:70]}»")

def build(slug):
    T = importlib.import_module(slug).TEST
    errs, warn = [], []
    pub = {k: T[k] for k in ("slug", "number", "title", "free")}
    key = {"slug": slug, "items": {}, "transcripts": []}
    # ---------- Listening ----------
    pl = {"parts": []}
    nums = []
    for pi, part in enumerate(T["listening"]["parts"]):
        script = part["script"]
        corpus = norm(" ".join(l.get("t", "") for l in script))
        names = {"N": "Narrator", **{k: v["name"] for k, v in part["speakers"].items()}}
        for l in script:
            if "s" in l and l["s"] not in names: errs.append(f"L{pi+1}: unknown speaker {l['s']}")
        key["transcripts"].append([{"s": l["s"], "name": names[l["s"]], "t": l["t"]} for l in script if "t" in l])
        groups, ns = [], []
        for g in part["groups"]:
            pg, qn = split_group(g, slug, "l", corpus, f"L{pi+1}", key, errs)
            groups.append(pg); ns += qn
        nums += ns
        pl["parts"].append({"label": part["label"], "range": f"{min(ns)}–{max(ns)}", "speakers": names, "groups": groups,
                            "audio": f"{slug}/part{pi+1}.mp3"})
    if sorted(nums) != list(range(1, 41)): errs.append(f"Listening numbers not 1–40: {sorted(nums)}")
    pub["listening"] = pl
    # ---------- Reading ----------
    pr = {"minutes": T["reading"]["minutes"], "passages": []}
    nums = []
    for pi, ps in enumerate(T["reading"]["passages"]):
        corpus = norm(" ".join(p[1] for p in ps["paras"]))
        global PARAS; PARAS = ps["paras"]
        groups, ns = [], []
        for g in ps["groups"]:
            pg, qn = split_group(g, slug, "r", corpus, f"R{pi+1}", key, errs)
            groups.append(pg); ns += qn
        nums += ns
        words = len(" ".join(p[1] for p in ps["paras"]).split())
        if words < 600: warn.append(f"R{pi+1}: passage only {words} words")
        pr["passages"].append({"title": ps["title"], "intro": ps.get("intro", ""), "paras": ps["paras"], "groups": groups, "range": f"{min(ns)}–{max(ns)}", "words": words})
    if sorted(nums) != list(range(1, 41)): errs.append(f"Reading numbers not 1–40: {sorted(nums)}")
    pub["reading"] = pr
    # answer distribution report
    dist = {}
    for k, v in key["items"].items():
        if "answer" in v and isinstance(v["answer"], str) and len(v["answer"]) <= 9: dist.setdefault(k.split("-")[1][0], []).append(v["answer"])
    json.dump(pub, open(os.path.join(OUT, f"{slug}.public.json"), "w"), ensure_ascii=False)
    json.dump(key, open(os.path.join(OUT, f"{slug}.key.json"), "w"), ensure_ascii=False)
    script_out = [{"label": p["label"], "speakers": p["speakers"], "script": p["script"]} for p in T["listening"]["parts"]]
    json.dump(script_out, open(os.path.join(OUT, f"{slug}.script.json"), "w"), ensure_ascii=False)
    return errs, warn, dist

def split_group(g, slug, mod, corpus, where, key, errs):
    pg = {k: v for k, v in g.items() if k != "qs"}
    pg["qs"] = []
    ns = []
    tokens = set(re.findall(r"\{\{(\d+)\}\}", json.dumps({k: g.get(k) for k in ("lines", "text", "table", "steps")})))
    for q in g["qs"]:
        qns = q.get("ns", [q["n"]])
        ns += qns
        qid = f"{slug}-{mod}{q['n']}"
        pq = {k: v for k, v in q.items() if k not in KEY_FIELDS}
        pq["id"] = qid
        if q["type"] in FIXED: pq["options"] = {v: v for v in FIXED[q["type"]]}
        pg["qs"].append(pq)
        k = {f: q[f] for f in KEY_FIELDS if f in q}
        k["n"] = q["n"]; k["ns"] = qns; k["type"] = q["type"]; k["limit"] = q.get("limit")
        key["items"][qid] = k
        w = f"{where} Q{q['n']}"
        if g["kind"] in ("notes", "form", "summary", "table", "flow") and g["kind"] != "form" and str(q["n"]) not in tokens:
            errs.append(f"{w}: no {{{{{q['n']}}}}} token in group text")
        for t in list(q.get("traps", {}).values()) + list(q.get("distract", {}).values()) + [q.get("def", "paraphrase_miss")]:
            if t not in TRAPS: errs.append(f"{w}: unknown trap {t}")
        if q["type"] == "gap":
            if not q.get("accept"): errs.append(f"{w}: no accept list")
            for a in q.get("accept", []):
                if len(a.split()) > (q.get("limit") or 1) and not re.match(r"^[\d,. ]+$", a): errs.append(f"{w}: accepted answer «{a}» breaks the word limit")
            if mod == "r" and not any(norm(a) in corpus for a in q["accept"]): errs.append(f"{w}: no accepted answer appears in the passage")
        else:
            opts = q.get("options") or FIXED.get(q["type"]) or g.get("box") or {l: l for l in g.get("letters", [])}
            opts = list(opts.keys()) if isinstance(opts, dict) else opts
            ans = q["answer"] if isinstance(q["answer"], list) else [q["answer"]]
            for a in ans:
                if a not in opts: errs.append(f"{w}: answer {a} not in options {opts}")
            if q["type"] == "multi" and len(ans) != q.get("pick", 2): errs.append(f"{w}: multi needs {q.get('pick')} answers")
        if q.get("evidence"):
            check_evidence(q["evidence"], corpus, w, errs)
            if mod == "r" and PARAS is not None:
                frag = norm([f.strip(" .,…") for f in re.split(r"…|\.\.\. ", q["evidence"]) if len(f.strip()) > 5][0])
                for i, (lab, txt) in enumerate(PARAS):
                    if frag in norm(txt): k["para"] = lab or str(i + 1); break
        else: errs.append(f"{w}: no evidence")
        if not q.get("why"): errs.append(f"{w}: no explanation")
    return pg, ns

if __name__ == "__main__":
    sys.path.insert(0, HERE)
    bad = False
    for slug in sys.argv[1:]:
        errs, warn, dist = build(slug)
        print(f"== {slug}: {len(errs)} errors, {len(warn)} warnings")
        for e in errs: print("  ERROR", e)
        for w in warn: print("  warn ", w)
        for m, a in dist.items():
            from collections import Counter
            print(f"  {m} answer spread:", dict(Counter(a)))
        bad |= bool(errs)
    sys.exit(1 if bad else 0)
