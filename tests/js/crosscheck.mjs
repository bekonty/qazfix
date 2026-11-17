// qazfix.js must give exactly the same answers as the Python package.
//   python scripts/make_js_fixtures.py web/model.json tests/js/fixtures.json
//   node tests/js/crosscheck.mjs web/model.json tests/js/fixtures.json
import { readFileSync } from "node:fs";
import { Qazfix } from "../../web/qazfix.js";

const [modelPath = "web/model.json", fixturePath = "tests/js/fixtures.json"] = process.argv.slice(2);
const q = new Qazfix(JSON.parse(readFileSync(modelPath, "utf8")));
const fx = JSON.parse(readFileSync(fixturePath, "utf8"));

let checked = 0;
const failures = [];
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

for (const [text, expected] of fx.restore) {
  checked++;
  const got = q.restore(text);
  if (got !== expected) failures.push(["restore", text, expected, got]);
}
for (const [word, expected, auto] of fx.candidates) {
  checked++;
  const got = q.candidates(word, 3).map((s) => [s.word, s.score]);
  if (!same(got, expected)) failures.push(["candidates", word, expected, got]);
  const gotAuto = q.shouldAutocorrect(word);
  if (gotAuto !== auto) failures.push(["shouldAutocorrect", word, auto, gotAuto]);
}
for (const [prefix, expected] of fx.complete) {
  checked++;
  const got = q.complete(prefix, 3).map((s) => [s.word, s.score]);
  if (!same(got, expected)) failures.push(["complete", prefix, expected, got]);
}

if (failures.length) {
  for (const [fn, input, want, got] of failures.slice(0, 20)) {
    console.log(`${fn}(${JSON.stringify(input)})\n  python: ${JSON.stringify(want)}\n  js:     ${JSON.stringify(got)}`);
  }
  console.log(`\nFAIL: ${failures.length} of ${checked} differ`);
  process.exit(1);
}
console.log(`OK: JavaScript matches Python on all ${checked} inputs`);
