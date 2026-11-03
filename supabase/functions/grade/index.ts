import { createClient } from "jsr:@supabase/supabase-js@2";
// Shared marking logic: used by the Supabase edge function and by the private preview build.
const BAND_TABLES: any = {
  reading: [[39,9],[37,8.5],[35,8],[33,7.5],[30,7],[27,6.5],[23,6],[19,5.5],[15,5],[13,4.5],[10,4],[8,3.5],[6,3],[4,2.5],[0,2]],
  listening: [[39,9],[37,8.5],[35,8],[32,7.5],[30,7],[26,6.5],[23,6],[18,5.5],[16,5],[13,4.5],[10,4],[8,3.5],[6,3],[4,2.5],[0,2]]
};
function bandFrom(module: string, raw: number, total: number) { const s = Math.round(raw / total * 40); return BAND_TABLES[module].find(([m]) => s >= m)[1]; }
function gNorm(s: any) { return String(s || "").toLowerCase().replace(/[£$]/g, "").replace(/:/g, ".").replace(/[’‘]/g, "'").replace(/\s+/g, " ").trim().replace(/[,!]+$/, "").replace(/\.$/, ""); }
function gLev(a: string, b: string) { const m = a.length, n = b.length; const d = Array.from({ length: m + 1 }, (_, i) => [i, ...Array(n).fill(0)]); for (let j = 1; j <= n; j++) d[0][j] = j; for (let i = 1; i <= m; i++) for (let j = 1; j <= n; j++) d[i][j] = Math.min(d[i-1][j] + 1, d[i][j-1] + 1, d[i-1][j-1] + (a[i-1] === b[j-1] ? 0 : 1)); return d[m][n]; }
function markGap(k: any, given: string) {
  const g = gNorm(given); if (!g) return { ok: false, trap: "unanswered" };
  const acc = k.accept.map(gNorm);
  if (acc.includes(g) || acc.includes(g.replace(/\s+/g, ""))) return { ok: true };
  if (g.split(" ").filter(Boolean).length > (k.limit || 1)) return { ok: false, trap: "word_limit" };
  const dk = k.distract ? Object.fromEntries(Object.entries(k.distract).map(([a, b]) => [gNorm(a), b])) : {};
  if (dk[g]) return { ok: false, trap: dk[g] };
  if (acc.some(a => a + "s" === g || a === g + "s" || a + "es" === g || a === g + "es")) return { ok: false, trap: "plural" };
  if (acc.some(a => !/^\d/.test(a) && gLev(a, g) <= (a.length >= 5 ? 2 : 1))) return { ok: false, trap: "spelling" };
  return { ok: false, trap: k.def || "paraphrase_miss" };
}
// keyItems: { id: {type, n, ns, answer|accept, ...} }, answers: { id: string | string[] }
function markAll(module: string, keyItems: any, answers: any) {
  const items = [];
  for (const [id, k] of Object.entries(keyItems)) {
    const info = { why: k.why, evidence: k.evidence, para: k.para || null };
    if (k.type === "multi") {
      const picked = Array.isArray(answers[id]) ? answers[id].slice(0, k.ns.length) : [];
      const right = k.answer.slice(); const wrong = picked.filter(x => !right.includes(x));
      let hits = picked.filter(x => right.includes(x));
      k.ns.forEach((n, i) => {
        const ok = i < hits.length;
        const missTrap = wrong[i - hits.length] ? ((k.traps || {})[wrong[i - hits.length]] || k.def || "lost_track") : "unanswered";
        items.push({ q: id, n, given: picked[i] || "", correct: right.join(" + "), ok, trap: ok ? null : missTrap, ...info });
      });
      continue;
    }
    const given = typeof answers[id] === "string" ? answers[id] : "";
    let r;
    if (k.type === "gap") r = markGap(k, given);
    else if (!given) r = { ok: false, trap: "unanswered" };
    else if (given === k.answer) r = { ok: true };
    else r = { ok: false, trap: (k.traps || {})[given] || k.def || "paraphrase_miss" };
    items.push({ q: id, n: k.n, given, correct: k.type === "gap" ? k.accept[0] : k.answer, ok: r.ok, trap: r.trap || null, ...info });
  }
  items.sort((a, b) => a.n - b.n);
  const raw = items.filter(i => i.ok).length;
  return { raw, total: items.length, band: bandFrom(module, raw, items.length), items };
}

const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type", "Access-Control-Allow-Methods": "POST, OPTIONS" };
const json = (b: unknown, status = 200) => new Response(JSON.stringify(b), { status, headers: { ...CORS, "Content-Type": "application/json" } });
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json({ error: "method" }, 405);
  let b: any; try { b = await req.json(); } catch { return json({ error: "bad_json" }, 400); }
  const { anon, slug, module, answers, mode, left, duration } = b || {};
  if (!UUID.test(String(anon)) || typeof slug !== "string" || !["reading", "listening"].includes(module) || typeof answers !== "object" || !answers) return json({ error: "bad_input" }, 400);
  if (JSON.stringify(answers).length > 20000) return json({ error: "too_large" }, 413);
  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, { auth: { persistSession: false } });
  const { data: t } = await db.from("tests").select("slug, free, published").eq("slug", slug).maybeSingle();
  if (!t || !t.published) return json({ error: "not_found" }, 404);
  const { data: u } = await db.from("users").select("plan").eq("anon_id", anon).maybeSingle();
  if (!t.free && (!u || u.plan === "free")) return json({ error: "locked" }, 403);
  const { data: k } = await db.from("test_keys").select("key").eq("slug", slug).single();
  const tag = `${slug}-${module[0]}`;
  const keyItems = Object.fromEntries(Object.entries(k.key.items).filter(([id]) => id.startsWith(tag) && /\d+$/.test(id.slice(tag.length))));
  const res = markAll(module, keyItems, answers);
  await db.from("users").upsert({ anon_id: anon, last_seen_at: new Date().toISOString() }, { onConflict: "anon_id", ignoreDuplicates: false });
  const { data: att } = await db.from("attempts").insert({ anon_id: anon, module, score: res.raw, total: res.total, band: res.band, duration_sec: Number(duration) || null,
    answers: { ...answers, _left: Number(left) || 0 }, test_slug: slug, mode: mode === "practice" ? "practice" : "exam" }).select("id").single();
  const wrong = res.items.filter((i: any) => !i.ok);
  if (att && wrong.length) await db.from("mistakes").insert(wrong.map((i: any) => ({ attempt_id: att.id, anon_id: anon, module, question_id: i.q + (i.n ? "#" + i.n : ""), trap: i.trap, user_answer: String(i.given).slice(0, 200), correct_answer: String(i.correct).slice(0, 200) })));
  return json({ ...res, attempt_id: att?.id ?? null, transcripts: module === "listening" ? k.key.transcripts : undefined });
});
