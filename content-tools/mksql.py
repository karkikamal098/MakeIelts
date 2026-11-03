import json,sys
for s in sys.argv[1:]:
    p=json.load(open(f'build/{s}.public.final.json')); k=json.load(open(f'build/{s}.key.json'))
    pj=json.dumps(p,ensure_ascii=False,separators=(',',':')); kj=json.dumps(k,ensure_ascii=False,separators=(',',':'))
    assert '$J$' not in pj and '$K$' not in kj
    t=p['title'].replace("'","''")
    sql=(f"insert into public.tests(slug,number,title,free,published,public) values ('{s}',{p['number']},'{t}',{str(p['free']).lower()},true,$J${pj}$J$::jsonb) on conflict (slug) do update set public=excluded.public,title=excluded.title,free=excluded.free,number=excluded.number,published=true;\n"
         f"insert into public.test_keys(slug,key) values ('{s}',$K${kj}$K$::jsonb) on conflict (slug) do update set key=excluded.key;\n")
    open(f'build/{s}.sql','w').write(sql); print(s,len(sql))
