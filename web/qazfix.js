// qazfix.js: restore Kazakh letters (ә ғ қ ң ө ұ ү і һ) in text typed without them.
//
// A line-by-line port of the Python package (src/qazfix). It must give the SAME
// answers: tests/js/crosscheck.mjs compares the two on held-out text in CI.
// Runs in browsers and Node, no dependencies.
//
//   import { loadModel } from "./qazfix.js";
//   const q = await loadModel("model.json");
//   q.restore("Мен казак тилинде сойлеймин");   // "Мен қазақ тілінде сөйлеймін"
//   q.candidates("казак");                      // [{word: "қазақ", score: 0.9628}, ...]
//   q.shouldAutocorrect("казак");               // "қазақ" or null
//   q.complete("казакс");                       // [{word: "қазақстан", score: 0.4}, ...]

// ---------------------------------------------------------------- letters
const STRIP_LOWER = [
  ["ә", "а"], ["ғ", "г"], ["қ", "к"], ["ң", "н"], ["ө", "о"],
  ["ұ", "у"], ["ү", "у"], ["і", "и"], ["һ", "х"],
];
const STRIP = new Map();
for (const [k, v] of STRIP_LOWER) STRIP.set(k, v);
for (const [k, v] of STRIP_LOWER) STRIP.set(k.toUpperCase(), v.toUpperCase());
const SPECIAL = new Set(STRIP.keys());

// plain letter -> possible real letters, plain first (same order as Python)
const OPTIONS = new Map();
for (const [special, plain] of STRIP_LOWER) {
  if (!OPTIONS.has(plain)) OPTIONS.set(plain, [plain]);
  OPTIONS.get(plain).push(special);
}
const AMBIGUOUS = new Set(OPTIONS.keys());
const LATIN_LOOKALIKES = { i: "і", I: "І" };
const CYRILLIC = new Set(
  "абвгғдеёжзийкқлмнңоөпрстуұүфхһцчшщъыіьэюя" +
  "АБВГҒДЕЁЖЗИЙКҚЛМНҢОӨПРСТУҰҮФХҺЦЧШЩЪЫІЬЭЮЯ",
);

export function strip(text) {
  let out = "";
  for (const ch of text) out += STRIP.get(ch) ?? ch;
  return out;
}

function harmony(stripped) {
  const lw = stripped.toLowerCase();
  const front = [...lw].some((c) => c === "е" || c === "э");
  const back = lw.includes("ы");
  if (front && !back) return "F";
  if (back && !front) return "B";
  return "?";
}

const isCyrillicWord = (t) => [...t].some((c) => CYRILLIC.has(c));
const hasSpecial = (t) => [...t].some((c) => SPECIAL.has(c));
const hasAmbiguous = (t) => [...t].some((c) => AMBIGUOUS.has(c));

// ---------------------------------------------------------------- model rules
const MAX_WINDOW = 4;
const MAX_Y_SWAPS = 4;
const LAUGHTER = /^(?:х[аеоы]|[аеоы]х)+х?$/;
const CHAT_WORDS = new Set(["ок", "окок", "ия"]);

const SMOOTHING = 0.5;
const TYPED_PRIOR = 0.6;
const BEAM = 12;
const AUTOCORRECT_THRESHOLD = 0.8;
const DICT_WEIGHT = 0.9;
const Y_WEIGHT = 0.6;

function* contexts(s, i, harm) {
  const p = "^" + s + "$";
  const j = i + 1;
  const c = s[i];
  for (let k = MAX_WINDOW; k >= 0; k--) {
    const left = p.slice(Math.max(0, j - k), j);
    const right = p.slice(j + 1, j + 1 + k);
    if (harm !== null) yield `${harm}|${k}|${left}|${c}|${right}`;
    yield `*|${k}|${left}|${c}|${right}`;
  }
}

// Python's itertools.combinations order
function* combinations(arr, r, start = 0, acc = []) {
  if (acc.length === r) { yield acc.slice(); return; }
  for (let i = start; i < arr.length; i++) {
    acc.push(arr[i]);
    yield* combinations(arr, r, i + 1, acc);
    acc.pop();
  }
}

function* ySwaps(s) {
  const spots = [];
  for (let i = 0; i < s.length; i++) if (s[i] === "ы") spots.push(i);
  if (!spots.length || spots.length > MAX_Y_SWAPS) return;
  for (let r = 1; r <= spots.length; r++) {
    for (const chosen of combinations(spots, r)) {
      const set = new Set(chosen);
      yield [...s].map((c, i) => (set.has(i) ? "и" : c)).join("");
    }
  }
}

// Python tuple order for (number, string) pairs, descending
const byScoreThenWordDesc = (a, b) => (b[0] - a[0]) || (a[1] < b[1] ? 1 : a[1] > b[1] ? -1 : 0);

// Python round(x, 4): correct rounding of the exact binary value, ties to even.
// toFixed rounds ties up, so exact ties (e.g. 0.15625 = 5/32) are handled here.
function round4(x) {
  const [ip, fp] = x.toFixed(30).split(".");
  if (/^50*$/.test(fp.slice(4))) {
    const down = Number(`${ip}.${fp.slice(0, 4)}`);
    return Number(fp[3]) % 2 === 0 ? down : Number((down + 0.0001).toFixed(4));
  }
  return Number(x.toFixed(4));
}

function isUpperPy(t) {
  let cased = false;
  for (const c of t) {
    const lo = c.toLowerCase(), up = c.toUpperCase();
    if (lo !== up) {
      cased = true;
      if (c !== up) return false;
    }
  }
  return cased;
}

function matchCase(template, word) {
  if (isUpperPy(template) && template.length > 1) return word.toUpperCase();
  if (template.length && isUpperPy(template[0])) return word[0].toUpperCase() + word.slice(1);
  return word;
}

function applyCase(template, lower) {
  const t = [...template], l = [...lower];
  return l.map((r, i) => (isUpperPy(t[i]) ? r.toUpperCase() : r)).join("");
}

// Same as Python's [^\W\d_]: letters plus non-decimal numerals (², ½, Ⅷ)
const LETTER = "[\\p{L}\\p{Nl}\\p{No}]";
const TOKEN = new RegExp(`${LETTER}+(?:[-'’]${LETTER}+)*`, "gu");

// ---------------------------------------------------------------- the model
export class Qazfix {
  constructor(data) {
    if (data.format !== 1) throw new Error(`unsupported model format ${data.format}`);
    this.words = data.words;
    this.chars = data.chars;
    this.russian = new Set(data.russian);
    this.useHarmony = Boolean(data.meta && data.meta.harmony);
    this.keys = Object.keys(this.words).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  }

  best(key) {
    let bestW = null, bestC = -Infinity;
    for (const [w, c] of Object.entries(this.words[key])) if (c > bestC) { bestW = w; bestC = c; }
    return bestW;
  }

  yAsI(s) {
    let best = null, bestCount = 0;
    for (const cand of ySwaps(s)) {
      if (Object.hasOwn(this.words, cand)) {
        const spelling = this.best(cand);
        const count = this.words[cand][spelling];
        if (count > bestCount) { best = spelling; bestCount = count; }
      }
    }
    return best;
  }

  restoreWord(lower) {
    if (hasSpecial(lower)) return lower;
    const s = lower;
    if (!hasAmbiguous(s)) return s;
    if (CHAT_WORDS.has(s) || LAUGHTER.test(s)) return s;
    if (Object.hasOwn(this.words, s)) return this.best(s);
    const swapped = this.yAsI(s);
    if (swapped) return swapped;
    if (this.russian.has(s)) return s;
    const harm = this.useHarmony ? harmony(s) : null;
    const out = [...s];
    for (let i = 0; i < s.length; i++) {
      const ch = s[i];
      if (!AMBIGUOUS.has(ch)) continue;
      for (const key of contexts(s, i, harm)) {
        const counts = this.chars[key];
        if (counts) {
          let bestO = null, bestC = -Infinity;
          for (const o of OPTIONS.get(ch)) {
            const c = counts[o] ?? 0;
            if (c > bestC) { bestO = o; bestC = c; }
          }
          out[i] = bestO;
          break;
        }
      }
    }
    return out.join("");
  }

  restore(text) {
    return text.replace(TOKEN, (token) => {
      if (!isCyrillicWord(token)) return token;
      const t = [...token].map((c) => LATIN_LOOKALIKES[c] ?? c).join("");
      return applyCase(t, this.restoreWord(t.toLowerCase()));
    });
  }

  // ------------------------------------------------------------ keyboard
  share(key) {
    const spellings = this.words[key];
    if (!spellings) return new Map();
    const entries = Object.entries(spellings);
    let total = 0;
    for (const [, c] of entries) total += c;
    return new Map(entries.map(([w, c]) => [w, c / total]));
  }

  yShare(s) {
    const counts = new Map();
    for (const key of ySwaps(s)) {
      const sp = this.words[key];
      if (!sp) continue;
      for (const [w, c] of Object.entries(sp)) counts.set(w, (counts.get(w) ?? 0) + c);
    }
    let total = 0;
    for (const c of counts.values()) total += c;
    if (!total) return new Map();
    return new Map([...counts].map(([w, c]) => [w, c / total]));
  }

  letterProbs(s, i) {
    const opts = OPTIONS.get(s[i]);
    const harm = this.useHarmony ? harmony(s) : null;
    for (const key of contexts(s, i, harm)) {
      const counts = this.chars[key];
      if (counts) {
        let sum = 0;
        for (const o of opts) sum += counts[o] ?? 0;
        const total = sum + SMOOTHING * opts.length;
        return opts.map((o) => [o, ((counts[o] ?? 0) + SMOOTHING) / total]);
      }
    }
    const rest = (1 - TYPED_PRIOR) / (opts.length - 1);
    return opts.map((o) => [o, o === s[i] ? TYPED_PRIOR : rest]);
  }

  charDistribution(s) {
    let beam = [[1.0, ""]];
    for (let i = 0; i < s.length; i++) {
      const ch = s[i];
      if (!AMBIGUOUS.has(ch)) {
        beam = beam.map(([p, w]) => [p, w + ch]);
        continue;
      }
      const probs = this.letterProbs(s, i);
      const next = [];
      for (const [p, w] of beam) for (const [o, q] of probs) next.push([p * q, w + o]);
      next.sort(byScoreThenWordDesc);
      beam = next.slice(0, BEAM);
    }
    let total = 0;
    for (const [p] of beam) total += p;
    const out = new Map();
    for (const [p, w] of beam) out.set(w, p / total);
    return out;
  }

  candidates(typed, n = 3) {
    const s = typed.toLowerCase();
    if (hasSpecial(s) || CHAT_WORDS.has(s) || LAUGHTER.test(s)) return [{ word: typed, score: 1.0 }];
    if (![...s].some((c) => AMBIGUOUS.has(c) || c === "ы")) return [{ word: typed, score: 1.0 }];

    const charP = this.charDistribution(s);
    const dictP = this.share(s);
    const yP = dictP.size ? new Map() : this.yShare(s);
    let scores;
    if (dictP.size) scores = mix(dictP, DICT_WEIGHT, charP);
    else if (yP.size) scores = mix(yP, Y_WEIGHT, charP);
    else if (this.russian.has(s)) scores = mix(new Map([[s, 1.0]]), 0.7, charP);
    else scores = charP;

    let ranked = [...scores].map(([w, p], idx) => [w, p, idx]);
    ranked.sort((a, b) => (b[1] - a[1]) || (a[2] - b[2])); // stable, like Python's sorted
    ranked = ranked.map(([w, p]) => [w, p]);
    const top = this.restoreWord(s);
    if (ranked.length && ranked[0][0] !== top) {
      const found = ranked.find(([w]) => w === top);
      const topScore = found ? found[1] : 0.0;
      const rest = [];
      ranked.forEach(([w, p], i) => { if (w !== top) rest.push([w, i === 0 ? topScore : p]); });
      ranked = [[top, ranked[0][1]], ...rest];
      const keyed = ranked.map(([w, p], idx) => [w, p, w !== top ? -p : -2.0, idx]);
      keyed.sort((a, b) => (a[2] - b[2]) || (a[3] - b[3]));
      ranked = keyed.map(([w, p]) => [w, p]);
    }
    return ranked.slice(0, n).map(([w, p]) => ({ word: matchCase(typed, w), score: round4(p) }));
  }

  shouldAutocorrect(typed, threshold = AUTOCORRECT_THRESHOLD) {
    const best = this.candidates(typed, 1)[0];
    return best.word !== typed && best.score >= threshold ? best.word : null;
  }

  complete(prefix, n = 3, scanLimit = 200000) {
    const p = prefix.toLowerCase();
    if ([...p].length < 2) return [];
    const sp = strip(p);
    const fixed = [];
    [...p].forEach((c, i) => { if (SPECIAL.has(c)) fixed.push([i, c]); });
    let lo = 0, hi = this.keys.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (this.keys[mid] < sp) lo = mid + 1; else hi = mid;
    }
    const found = [];
    let total = 0;
    for (let i = lo, scanned = 0; i < this.keys.length && this.keys[i].startsWith(sp) && scanned < scanLimit; i++, scanned++) {
      for (const [spelling, count] of Object.entries(this.words[this.keys[i]])) {
        if (fixed.every(([j, c]) => spelling[j] === c)) {
          found.push([count, spelling]);
          total += count;
        }
      }
    }
    found.sort(byScoreThenWordDesc);
    return found.slice(0, n).map(([c, w]) => ({ word: matchCase(prefix, w), score: round4(c / total) }));
  }
}

function mix(primary, weight, secondary) {
  const out = new Map();
  for (const [w, p] of primary) out.set(w, weight * p);
  for (const [w, p] of secondary) out.set(w, (out.get(w) ?? 0.0) + (1 - weight) * p);
  return out;
}

export async function loadModel(source = "model.json") {
  if (typeof source === "object") return new Qazfix(source);
  const res = await fetch(source);
  if (!res.ok) throw new Error(`could not load ${source}: ${res.status}`);
  return new Qazfix(await res.json());
}
