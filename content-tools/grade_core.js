// Shared marking logic: used by the Supabase edge function and by the private preview build.
const BAND_TABLES = {
  reading: [[39,9],[37,8.5],[35,8],[33,7.5],[30,7],[27,6.5],[23,6],[19,5.5],[15,5],[13,4.5],[10,4],[8,3.5],[6,3],[4,2.5],[0,2]],
  listening: [[39,9],[37,8.5],[35,8],[32,7.5],[30,7],[26,6.5],[23,6],[18,5.5],[16,5],[13,4.5],[10,4],[8,3.5],[6,3],[4,2.5],[0,2]]
};
function bandFrom(module, raw, total) { const s = Math.round(raw / total * 40); return BAND_TABLES[module].find(([m]) => s >= m)[1]; }
function gNorm(s) { return String(s || "").toLowerCase().replace(/[£$]/g, "").replace(/:/g, ".").replace(/[’‘]/g, "'").replace(/\s+/g, " ").trim().replace(/[,!]+$/, "").replace(/\.$/, ""); }
function gLev(a, b) { const m = a.length, n = b.length; const d = Array.from({ length: m + 1 }, (_, i) => [i, ...Array(n).fill(0)]); for (let j = 1; j <= n; j++) d[0][j] = j; for (let i = 1; i <= m; i++) for (let j = 1; j <= n; j++) d[i][j] = Math.min(d[i-1][j] + 1, d[i][j-1] + 1, d[i-1][j-1] + (a[i-1] === b[j-1] ? 0 : 1)); return d[m][n]; }
function markGap(k, given) {
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
function markAll(module, keyItems, answers) {
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
