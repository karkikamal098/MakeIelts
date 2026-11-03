import json, sys
slug = sys.argv[1]
pub = json.load(open(f'build/{slug}.public.json')); sc = json.load(open(f'build/{slug}.script.json'))
L = [f"# makeielts {pub['title']} — candidate paper (no answers)\n", "## LISTENING (full transcript given instead of audio)\n"]
for p, s in zip(pub['listening']['parts'], sc):
    L.append(f"### {p['label']}\nTranscript:\n")
    for l in s['script']:
        if 't' in l: L.append(f"- {p['speakers'][l['s']]}: {l['t']}")
    L.append("\nQuestions:\n")
    for g in p['groups']:
        L.append(json.dumps({k: v for k, v in g.items() if k != 'svg'}, ensure_ascii=False))
        if g.get('svg'): L.append("MAP (SVG source; y grows downward, north is up):\n" + g['svg'])
L.append("\n## READING\n")
for ps in pub['reading']['passages']:
    L.append(f"### {ps['title']}\n")
    for i, (lab, t) in enumerate(ps['paras']): L.append(f"[{lab or i+1}] {t}\n")
    L.append("Questions:\n")
    for g in ps['groups']: L.append(json.dumps(g, ensure_ascii=False))
open(f'check/{slug}_paper.md', 'w').write("\n".join(L))
