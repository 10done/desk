// TPOT is the mean gap between revealed pieces. Total is the playhead on the recorded clock.
function metricsAt(run, tMs) {
  var end = Number(run.stream_end_ms) || 0;
  var t = Math.min(Math.max(Number(tMs) || 0, 0), end);
  var seen = [];
  var tokens = run.tokens || [];
  for (var i = 0; i < tokens.length; i++) {
    if (tokens[i].t_ms <= t) seen.push(tokens[i]);
  }
  var ttft = seen.length ? seen[0].t_ms : null;
  var tpot = null;
  if (seen.length >= 2) {
    tpot = (seen[seen.length - 1].t_ms - seen[0].t_ms) / (seen.length - 1);
  }
  var phase = tokens.length && t >= tokens[0].t_ms ? "decode" : "prefill";
  var text = "";
  for (var j = 0; j < seen.length; j++) text += seen[j].text;
  return { t: t, ttft: ttft, tpot: tpot, total: t, phase: phase, text: text, n: seen.length };
}

// Mean over the decode span. Not a per-token arrival time: the API stamped pieces, not tokens.
function billedTpot(run) {
  var n = run.usage && Number(run.usage.output_tokens);
  var tokens = run.tokens || [];
  if (!n || n < 2 || tokens.length < 1) return null;
  return (tokens[tokens.length - 1].t_ms - tokens[0].t_ms) / (n - 1);
}

if (typeof module !== "undefined" && module.exports) module.exports = { metricsAt: metricsAt, billedTpot: billedTpot };
