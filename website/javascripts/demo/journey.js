/* Presentation helpers for real regression outputs; no inference or generated data. */
(() => {
  'use strict';
  const unit = value => (value - 1) / 254;
  // A small neutral band is an interface convention, not a trained classifier.
  const band = value => value < 116 ? -1 : value > 140 ? 1 : 0;
  function snapshot(pair) {
    if (!Array.isArray(pair) || pair.length !== 2 || pair.some(v => !Number.isFinite(v) || v < 1 || v > 255)) throw new Error('Invalid emotion coordinates');
    return {valence: band(pair[0]), arousal: band(pair[1]), x: unit(pair[0]), y: 1 - unit(pair[1]),
      mouth: 75 + (pair[0] - 128) / 127 * 24, eye: 2.4 + unit(pair[1]) * 4};
  }
  function summarize(pairs) {
    if (!Array.isArray(pairs) || !pairs.length) throw new Error('No predictions');
    pairs.forEach(snapshot);
    let moment = 0, maxStep = 0;
    for (let i = 1; i < pairs.length; i++) {
      const step = Math.hypot(pairs[i][0] - pairs[i - 1][0], pairs[i][1] - pairs[i - 1][1]);
      if (step > maxStep) { moment = i; maxStep = step; }
    }
    return {moment, maxStep, delta: pairs.at(-1).map((v, t) => v - pairs[0][t])};
  }
  const api = {snapshot, summarize};
  globalThis.VtpJourney = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
