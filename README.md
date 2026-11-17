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
can't. qazfix puts the letters back, using context and open Kazakh dictionaries.

- **Accurate:** 95.7% of words right on held-out text; the right word is in a 3-word suggestion bar
  98.9% of the time.
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
казак:  қазақ 95%  |  қазак 4%  |  қазәқ 0%   (auto-correct → қазақ)
баур:  бауыр 85%  |  баур 6%  |  баұр 4%   (auto-correct → бауыр)
кыргызды:  қырғызды 34%  |  қыргызды 26%  |  кырғызды 23%
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
| right word is suggestion #1 | 95.7% | 86.4% |
| right word is in the 3-word bar | **98.9%** | 88.8% |
| keystrokes saved by completion | 12.9% | 11.4% |

Auto-correct on space happens only above a confidence threshold. A wrong replacement annoys people
far more than a suggestion they tap, so the default (0.8) favours precision:

| threshold | precision (replacements that were right) | coverage (fixes done automatically) |
|---:|---:|---:|
| 0.5 | 96.6% | 87.3% |
| 0.7 | 98.3% | 81.0% |
| **0.8 (default)** | **98.8%** | **78.2%** |
| 0.95 | 99.6% | 48.3% |

## Chat shorthand: dropped vowels

In chat, people drop the reduced vowels ы and і: `баур` (бауыр), `бугн` (бүгін), `кеттк` (кеттік),
`жаздн` (жаздың), `бз` (біз). qazfix puts one or two of them back, but only when the result is a
dictionary word or a dictionary stem plus a real ending, and it picks ы or і to match the word's
vowel harmony (`колдаймн` → қолдаймын, not қолдаймін). Words that are already real (тілдерін =
тіл + дерін) and unknown shorthand (`почтт`) are left alone.

On held-out words with the last vowel removed (1,190 words): **81.7%** restored exactly.

## In the browser: `qazfix.js`

`web/qazfix.js` is a dependency-free JavaScript port for web pages and keyboards. CI checks that it
gives exactly the same answers as Python on about 10,000 generated inputs (known words, unseen
inflections, ы typed for і, shorthand, Russian stems, chat words, case).

```js
import { loadModel } from "./qazfix.js";
const q = await loadModel("model.json");   // make it with: qazfix export-web model.json
q.restore("биз бугн кеттк");               // "біз бүгін кеттік"
q.candidates("казак");                     // [{word: "қазақ", score: 0.9527}, ...]
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
document** so no test document was seen in training. Counted: the 4,574 test words with a letter to
decide.

| method | word accuracy | Kazakh letters restored | correct words left alone |
|---|---:|---:|---:|
| do nothing | 32.7% | 0.0% | 100.0% |
| word list only (unseen words unchanged) | 67.8% | 52.5% | 99.3% |
| + character context | 89.2% | 87.9% | 91.8% |
| + Russian-word guard (small corpus only) | 89.7% | 87.8% | 93.6% |
| **+ hunspell & Apertium dictionaries = qazfix** | **95.7%** | **94.9%** | **97.3%** |

Same text typed the chat way (і as ы): 80.1% → **86.4%** with the dictionaries.

**What this tells us:**
- Kazakh is agglutinative: endless inflected forms (`тілінде`, `тіліміздегі`…) appear in no word
  list. Deciding each letter from its neighbours takes accuracy from 68% to 89%.
- The open dictionaries add 6 points. Their 1.2 million word forms teach the character model, and
  their 71,000 stems (with names like Бекболат, Шымкент) fix most of the remaining errors.
- **Ideas that didn't work, kept for honesty:** vowel harmony as a context feature slightly hurt
  (89.5% vs 89.7%) and still doesn't help with the dictionaries (95.6% vs 95.7%) while doubling the
  model, so it is off. A guard that keeps real ы-words (`кыргызды` → қырғызды, not кіргізді) costs
  1 point on the simulated chat test but fixes real chat messages.
- Pruning: 550,000 character contexts → 39,000 with **no** accuracy change, so the whole model is
  1.1 MB.

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
| colloquial spellings in the subtitle corpus | `казыр → кәзір` | open: needs a bigger corpus (Wikipedia) |

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

python scripts/build_lexicon.py hunspell-kk/kk_KZ.dic hunspell-kk/kk_KZ.aff \
    apertium-kaz/apertium-kaz.kaz.lexc lexicon.txt stems.txt suffixes.txt
python scripts/prepare_ud.py UD_Kazakh-KTB data/          # train/test split by document
python scripts/russian_words.py 30000 > russian.txt

qazfix build kk_full.txt data/ud_train.txt --lexicon lexicon.txt --stems stems.txt \
    --suffixes suffixes.txt --russian russian.txt -o src/qazfix/data/model.json.gz
qazfix eval data/ud_test.txt                              # always measure on held-out text
python scripts/compare.py kk_full.txt data/ud_train.txt --test data/ud_test.txt \
    --russian russian.txt --lexicon lexicon.txt --stems stems.txt --suffixes suffixes.txt
```

**Biggest next step: a real corpus.** The word frequencies come from movie subtitles and a small
treebank. Adding Kazakh Wikipedia (`scripts/wikipedia_text.py`) as another corpus file should fix
colloquial spellings and rare names.

## Roadmap

- [x] v0.1: library, CLI, character-context model, Russian guard, honest evaluation
- [x] v0.1.1: fixes from real chat testing
- [x] v0.2: keyboard mode: ranked suggestions, confident auto-correct, completion
- [x] v0.3: JavaScript port, exact Python-vs-JS check in CI, demo page on GitHub Pages
- [x] v0.4: hunspell + Apertium dictionaries, dropped-vowel shorthand, Russian stems, pruning
- [ ] Kazakh Wikipedia as a frequency corpus
- [ ] Two-word context for true ambiguities (`казак`/`қазақ`, `шукыр`: шүкір or шұқыр)
- [ ] Suggestion bar in the Kazakh Adaptive Keyboard; Android keyboard

## License

Code: MIT. Bundled model data: GPL-3.0, because it is built from GPL-licensed dictionaries. See
[DATA_LICENSE.md](DATA_LICENSE.md) for every source.
