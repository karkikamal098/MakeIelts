import json, sys
slug = sys.argv[1]
k = json.load(open(f'build/{slug}.key.json'))['items']; a = json.load(open(f'check/{slug}_answers.json'))
n_ = lambda s: str(s).strip().lower()
mism = []
for qid, v in k.items():
    mod = 'listening' if '-l' in qid else 'reading'; got = a[mod].get(str(v['n']))
    if v['type'] == 'gap': ok = n_(got) in [n_(x) for x in v['accept']]
    elif v['type'] == 'multi': ok = sorted(got or []) == sorted(v['answer'])
    else: ok = n_(got) == n_(v['answer'])
    if not ok: mism.append((mod, v['n'], got, v.get('accept') or v.get('answer')))
print(slug, len(mism), 'mismatches'); [print(' ', m) for m in mism]
print(' flags:'); [print('  ', f) for f in a.get('flags', [])]
