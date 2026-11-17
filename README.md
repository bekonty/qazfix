# qazfix

**Restore Kazakh letters in text typed without them, and the vowels chat shorthand drops.**

```console
$ qazfix "Мен казак тилинде сойлеймин"
Мен қазақ тілінде сөйлеймін
$ qazfix "биз бугн кеттк"
біз бүгін кеттік
```

**Try it in your browser (phone or laptop, nothing to install): https://bekonty.github.io/qazfix/**

Kazakh has nine letters most keyboards make awkward: **ә ғ қ ң ө ұ ү і һ**. So people type
`казак тили` instead of `қазақ тілі`, and in chat they also drop vowels: `баур` for `бауыр`,
`бугн` for `бүгін`. Humans can read it; search, spell-checkers, text-to-speech and AI models
can't. qazfix puts the letters back, using context, open Kazakh dictionaries and word frequencies
from Kazakh Wikipedia.

- **Accurate:** 98.2% of words right on held-out text; the right word is in a 3-word suggestion bar
  99.7% of the time.
- **Keyboard-ready:** ranked suggestions, completion, auto-correct only when confident. About 0.04 ms
  per keystroke.
- **Safe:** keeps case, spacing and punctuation. Never touches a word you already typed with Kazakh
  letters, Russian words (`встреча`, `списокта`), chat words (`ок`) or laughter (`хахаха`).
- **Runs anywhere:** Python package and a dependency-free JavaScript port that gives exactly the
  same answers (checked in CI). Nothing is sent anywhere.
- **Honest:** every number below is measured on held-out text and reproducible.

## Install

```bash
pip install qazfix        # once published; for now: pip install git+https://github.com/bekonty/qazfix
```

## Use

```python
import qazfix

qazfix.restore("Биз ертен Алматыга барамыз")   # 'Біз ертең Алматыға барамыз'
qazfix.restore("КАЗАК ТИЛИ")                    # 'ҚАЗАҚ ТІЛІ'
qazfix.restore("Джим бараснба бугн")            # 'Джим бараснба бүгін'  (shorthand fixed, slang kept)
qazfix.restore("Ертен встреча бар ма?")         # 'Ертең встреча бар ма?' (Russian word kept)
```

```bash
qazfix "Казакстан Республикасы"     # → Қазақстан Республикасы
cat message.txt | qazfix -          # fix a whole file
```

## Keyboard mode (T9-style suggestions)

```console
$ qazfix suggest казак баур кыргызды
казак:  қазақ 97%  |  казак 1%  |  қазак 1%   (auto-correct → қазақ)
баур:  бауыр 85%  |  баур 7%  |  баұр 4%   (auto-correct → бауыр)
кыргызды:  қырғызды 93%  |  кырғызды 5%  |  қыргызды 2%   (auto-correct → қырғызды)
$ qazfix complete казакс
қазақстан  |  қазақстанның  |  қазақстанмен
```

```python
from qazfix.keyboard import Predictor

p = Predictor()
p.candidates("казак")          # suggestion bar after a word
p.should_autocorrect("баур")   # 'бауыр' → replace on space; None → just show suggestions
p.complete("казакст")          # suggestion bar while typing
```

Measured on held-out test text (`scripts/keyboard_eval.py`):

| | normal typing (і as и) | chat typing (і as ы) |
|---|---:|---:|
| right word is suggestion #1 | 98.2% | 93.1% |
| right word is in the 3-word bar | **99.7%** | 94.4% |
| keystrokes saved by completion | 17.1% | 15.1% |

Auto-correct on space happens only above a confidence threshold. A wrong replacement annoys people
far more than a suggestion they tap, so the default (0.8) favours precision:

| threshold | precision (replacements that were right) | coverage (fixes done automatically) |
|---:|---:|---:|
| 0.5 | 98.7% | 95.6% |
| 0.7 | 99.5% | 91.4% |
| **0.8 (default)** | **99.7%** | **89.6%** |
| 0.95 | 99.9% | 52.9% |

## Chat shorthand: dropped vowels

In chat, people drop the reduced vowels ы and і: `баур` (бауыр), `бугн` (бүгін), `кеттк` (кеттік),
`жаздн` (жаздың), `бз` (біз). qazfix puts one or two of them back, but only when the result is a
dictionary word or a dictionary stem plus a real ending, and it picks ы or і to match the word's
vowel harmony (`колдаймн` → қолдаймын, not қолдаймін). Words that are already real (тілдерін =
тіл + дерін) and unknown shorthand (`почтт`) are left alone.

On held-out words with the last vowel removed (1,096 words): **86.8%** restored exactly.

## In the browser: `qazfix.js`

`web/qazfix.js` is a dependency-free JavaScript port for web pages and keyboards. CI checks that it
gives exactly the same answers as Python on about 10,000 generated inputs (known words, unseen
inflections, ы typed for і, shorthand, Russian stems, chat words, case).

```js
import { loadModel } from "./qazfix.js";
const q = await loadModel("model.json");   // make it with: qazfix export-web model.json
q.restore("биз бугн кеттк");               // "біз бүгін кеттік"
q.candidates("казак");                     // [{word: "қазақ", ...}, ...]
q.shouldAutocorrect("баур");               // "бауыр" (or null when unsure)
q.complete("казакс");                      // [{word: "қазақстан", ...}, ...]
```

The demo page (`web/index.html`) shows a suggestion bar on the text box, auto-corrects on space only
when confident, and lets Backspace undo an auto-correction (it then won't redo that word).

```bash
qazfix export-web web/model.json
python -m http.server --directory web 8000    # open http://localhost:8000
```

## How well does it work?

Test: take **correctly written** Kazakh sentences, strip the special letters the way a keyboard
would, restore them, and compare with the original. Test sentences come from the
[UD Kazakh-KTB](https://github.com/UniversalDependencies/UD_Kazakh-KTB) treebank, split **by source
document** so no test document was seen in training. Because the model also learns word
frequencies from Kazakh Wikipedia, the three test documents that may come from Wikipedia are left
out (`ud_test_clean.txt`, 666 sentences). Counted: the 4,158 test words with a letter to decide.

| method | word accuracy | Kazakh letters restored | correct words left alone |
|---|---:|---:|---:|
| do nothing | 32.3% | 0.0% | 100.0% |
| word list only (unseen words unchanged) | 67.7% | 52.6% | 99.3% |
| + character context | 89.5% | 88.0% | 92.7% |
| + Russian-word guard (small corpus only) | 90.0% | 87.9% | 94.4% |
| + hunspell & Apertium dictionaries | 95.8% | 95.0% | 97.3% |
| **+ Kazakh Wikipedia word frequencies = qazfix** | **98.2%** | **97.8%** | **98.9%** |

| same test, typed differently | small corpus | + dictionaries | + Wikipedia |
|---|---:|---:|---:|
| chat style (і as ы: `быз`) | 80.1% | 88.0% | **93.1%** |
| shorthand, last vowel dropped (`бугн`) | 51.8% | 82.0% | **86.8%** |

**What this tells us:**
- Kazakh is agglutinative: endless inflected forms (`тілінде`, `тіліміздегі`…) appear in no word
  list. Deciding each letter from its neighbours takes accuracy from 68% to 90%.
- Open dictionaries add 6 points: 1.2 million word forms teach the character model, and 71,000
  stems (with names like Бекболат, Шымкент) fix most remaining errors.
- Real frequencies add 2.4 more: 29.6 million words of Wikipedia settle spellings the small corpus
  got wrong (`казир`: қазір 4,071 vs кәзір 38; `шукыр`: шүкір 107 vs шұқыр 17).
- With Wikipedia counts, a frequent ы→і reading beats a rare exact match (`казыр`, 20 noisy
  Wikipedia hits, → қазір) but not a real word (`тыс` 3,601 vs тіс 904: kept).
- **Ideas that didn't work, kept for honesty:**
  - vowel harmony as a context feature: no gain at any data size, doubles the model;
  - the neighbouring word (500k Wikipedia word pairs): +0.04 points for +0.8 MB, not shipped;
  - a bigger word table: Wikipedia words seen ≥5 times scored 98.4% but restored shorthand worse
    (78% vs 87%), because Wikipedia noise looks like shorthand. Words seen ≥20 times are kept.
- Pruning: 856,000 character contexts → 88,000 with no accuracy change; the model is 2.0 MB.

Reproduce: see [Build the model](#build-the-model).

## Real-world check: chat messages

Running qazfix on a real WhatsApp chat (casual, Kazakh mixed with Russian) found problems the
treebank test could not, and drove most of the features above:

| found in real chat | example | status |
|---|---|---|
| already-correct words got changed | `қазір → қәзір` | fixed |
| і typed as ы | `негызы`, `быреуы` | fixed |
| chat words became real but wrong words | `ок → оқ`, `хахаха → хаһаһа` | fixed |
| shorthand with dropped vowels | `бугн`, `кеттк`, `баур` | fixed (dictionary + harmony) |
| Russian stems with Kazakh endings | `списокта → спісоқта` | fixed |
| real ы-words swapped to і | `кыргызды → кіргізді` | fixed |
| colloquial spellings in the subtitle corpus | `казир → кәзір` | fixed by Wikipedia frequencies |
| rare/noisy exact matches | `казыр`, `шукыр` | fixed: frequent ы→і reading wins |
| shorthand with merged words, cut endings | `бараснба`, `бармайм` | open |

To measure on your own messages: `scripts/pair_eval.py` (keep chat files out of git).

## How it works

For each Cyrillic word (case is put back afterwards):

1. **Leave alone:** already has a Kazakh letter, a chat word, or laughter.
2. **Known word:** pick its most frequent valid spelling (`казак` → `қазақ`).
3. **і typed as ы:** try ы→і against the word table (`быз` → біз), unless the word is a real
   ы-word (қырғыз + ды).
4. **Russian:** a Russian word, or a Russian stem + Kazakh ending: keep the Russian part.
5. **Shorthand:** put back a dropped ы/і if that gives a dictionary word or stem + ending.
6. **Unseen word:** decide each letter from up to 4 letters on each side, backing off to smaller
   windows. This handles the endless inflected forms.

Details: [SPEC.md](SPEC.md).

## Build the model

The bundled model (`src/qazfix/data/model.json.gz`) is built like this:

```bash
pip install -e ".[build]"
git clone https://github.com/taem/hunspell-kk
git clone --depth 1 https://github.com/apertium/apertium-kaz
git clone https://github.com/UniversalDependencies/UD_Kazakh-KTB
curl -LO https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/kk/kk_full.txt
pip install datasets
python scripts/wikipedia_text.py kkwiki.txt               # Kazakh Wikipedia, ~238k articles
python scripts/word_counts.py kkwiki.txt kkwiki_words.txt

python scripts/build_lexicon.py hunspell-kk/kk_KZ.dic hunspell-kk/kk_KZ.aff \
    apertium-kaz/apertium-kaz.kaz.lexc lexicon.txt stems.txt suffixes.txt
python scripts/prepare_ud.py UD_Kazakh-KTB data/          # train/test split by document
python scripts/russian_words.py 30000 > russian.txt

qazfix build kk_full.txt data/ud_train.txt kkwiki_words.txt --lexicon lexicon.txt \
    --stems stems.txt --suffixes suffixes.txt --russian russian.txt --min-count 20 \
    -o src/qazfix/data/model.json.gz
qazfix eval data/ud_test_clean.txt                        # always measure on held-out text
python scripts/compare.py kk_full.txt data/ud_train.txt --test data/ud_test_clean.txt \
    --russian russian.txt --lexicon lexicon.txt --stems stems.txt --suffixes suffixes.txt \
    --wiki kkwiki_words.txt
```

**Next step: real typed text.** Wikipedia is formal. A few hundred real chat messages with
hand-corrected versions (`scripts/pair_eval.py`) would show how people actually type, and are the
honest test for a keyboard.

## Roadmap

- [x] v0.1: library, CLI, character-context model, Russian guard, honest evaluation
- [x] v0.1.1: fixes from real chat testing
- [x] v0.2: keyboard mode: ranked suggestions, confident auto-correct, completion
- [x] v0.3: JavaScript port, exact Python-vs-JS check in CI, demo page on GitHub Pages
- [x] v0.4: hunspell + Apertium dictionaries, dropped-vowel shorthand, Russian stems, pruning
- [x] v0.5: Kazakh Wikipedia word frequencies (29.6M words): 98.2% held-out, 99.7% top-3
- [ ] Hand-checked accuracy on real chat messages
- [ ] Merged words and cut endings in chat (`бараснба` = барасың ба)
- [ ] Suggestion bar in the Kazakh Adaptive Keyboard; Android keyboard

## License

Code: MIT. Bundled model data: GPL-3.0, because it is built from GPL-licensed dictionaries. See
[DATA_LICENSE.md](DATA_LICENSE.md) for every source.
