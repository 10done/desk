const fs = require("fs");
const path = require("path");
const { metricsAt, billedTpot } = require("../metrics.js");
const root = path.join(__dirname, "..");
const corpus = JSON.parse(fs.readFileSync(path.join(root, "corpus.json"), "utf8"));
const run = JSON.parse(fs.readFileSync(path.join(root, "data", "first-token.json"), "utf8"));

if (corpus.pages.length !== 14) throw new Error("pages");
if (corpus.questions.length !== 12) throw new Error("questions");
for (const q of corpus.questions) {
  const page = corpus.pages.find((p) => p.id === q.page);
  if (!page) throw new Error("missing " + q.page);
  if (!page.body.includes(q.answer)) throw new Error(q.id + " answer not in page");
}
if (run.series !== "one run") throw new Error("series");
if (!run.machine || !run.command) throw new Error("provenance");
if (run.tokens.length < 2) throw new Error("need two pieces");
for (let i = 1; i < run.tokens.length; i++) {
  if (run.tokens[i].t_ms < run.tokens[i - 1].t_ms) throw new Error("order");
}
const end = metricsAt(run, run.stream_end_ms);
if (end.ttft !== run.tokens[0].t_ms) throw new Error("ttft");
if (end.n !== run.tokens.length) throw new Error("seen");
const expect = (run.tokens[run.tokens.length - 1].t_ms - run.tokens[0].t_ms) / (run.tokens.length - 1);
if (Math.abs(end.tpot - expect) > 1e-9) throw new Error("tpot");
if (end.phase !== "decode") throw new Error("decode");
if (end.total !== run.stream_end_ms) throw new Error("total");
if (run.tokens[0].t_ms > 0) {
  const early = metricsAt(run, Math.max(0, run.tokens[0].t_ms - 0.001));
  if (run.tokens[0].t_ms - 0.001 > 0 && (early.phase !== "prefill" || early.ttft !== null)) {
    throw new Error("prefill");
  }
}
const mid = metricsAt(run, run.tokens[0].t_ms);
if (mid.tpot !== null) throw new Error("one piece has no tpot");
const mean = billedTpot(run);
const span = run.tokens[run.tokens.length - 1].t_ms - run.tokens[0].t_ms;
if (Math.abs(mean - span / (run.usage.output_tokens - 1)) > 1e-9) throw new Error("billed");
console.log(JSON.stringify({
  ttft_ms: end.ttft,
  tpot_ms: end.tpot,
  billed_tpot_ms: mean,
  total_ms: end.total,
  pieces: run.tokens.length,
  output_tokens: run.usage && run.usage.output_tokens,
  model: run.model
}));
