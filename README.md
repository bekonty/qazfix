# qazfix

**Restore Kazakh letters in text typed without them.**

```console
$ qazfix "Мен казак тилинде сойлеймин"
Мен қазақ тілінде сөйлеймін
```

Kazakh has nine letters most keyboards make awkward: **ә ғ қ ң ө ұ ү і һ**. So people type
`казак тили` instead of `қазақ тілі`. Humans can read it, but search, spell-checkers,
text-to-speech and AI models can't handle it properly. qazfix puts the letters back, using context
to tell `казак` (Cossack) from `қазақ` (Kazakh).

- **Fast and tiny:** about 70,000 words/second, a 210 KB model, zero dependencies.
- **Safe:** keeps case, spacing and punctuation exactly. Never changes a Kazakh letter you already
  typed. Leaves Russian words (`встреча`) and Latin text alone.
- **Honest:** accuracy is measured on held-out text, with baselines (below).

## Install

```bash
pip install qazfix        # once published; for now: pip install git+https://github.com/bekonty/qazfix
```

## Use

```python
import qazfix

qazfix.restore("Биз ертен Алматыга барамыз")   # 'Біз ертең Алматыға барамыз'
qazfix.restore("КАЗАК ТИЛИ")                    # 'ҚАЗАҚ ТІЛІ'
qazfix.restore("Ертен встреча бар ма?")         # 'Ертең встреча бар ма?'  (Russian word kept)
```

```bash
qazfix "Казакстан Республикасы"     # → Қазақстан Республикасы
cat message.txt | qazfix -          # fix a whole file
```

## Keyboard mode (T9-style suggestions)

For keyboards: a 3-word suggestion bar, auto-correct only when confident, and completion while
typing. About 0.04 ms per keystroke.

```console
$ qazfix suggest казак кыргызды Ок
казак:  қазақ 96%  |  қазәқ 1%  |  қазак 1%   (auto-correct → қазақ)
кыргызды:  кіргізді 60%  |  қырғызды 35%  |  қыргызды 3%
Ок:  Ок 100%
$ qazfix complete казакс
қазақстан  |  қазақстанның  |  қазақстанмен
```

```python
from qazfix.keyboard import Predictor

p = Predictor()
p.candidates("казак")          # suggestion bar after a word
p.should_autocorrect("казак")  # 'қазақ' → replace on space; None → just show suggestions
p.complete("казакст")          # suggestion bar while typing
```

Measured on the same held-out test text (`scripts/keyboard_eval.py`):

| | normal typing (і as и) | chat typing (і as ы) |
|---|---:|---:|
| right word is suggestion #1 | 89.7% | 76.1% |
| right word is in the 3-word bar | **96.8%** | 85.3% |
| keystrokes saved by completion | 10.7% | 9.7% |

Auto-correct on space happens only above a confidence threshold. A wrong auto-replacement annoys
people far more than a suggestion they have to tap, so the default (0.8) favours precision:

| threshold | precision (replacements that were right) | coverage (fixes done automatically) |
|---:|---:|---:|
| 0.5 | 93.6% | 80.7% |
| 0.7 | 97.6% | 65.9% |
| **0.8 (default)** | **98.6%** | **59.3%** |
| 0.95 | 99.7% | 43.8% |

(normal typing; the full table, including chat typing, comes from `scripts/keyboard_eval.py`)

## How well does it work?

Test: take **correctly written** Kazakh sentences, strip the special letters the way a keyboard
would, restore them, and compare with the original. The test sentences come from the
[UD Kazakh-KTB](https://github.com/UniversalDependencies/UD_Kazakh-KTB) treebank, split **by source
document** so no test document was seen during training. Counted: the 4,574 test words that contain
at least one letter qazfix has to decide on.

| method | word accuracy | Kazakh letters restored | correct words left alone |
|---|---:|---:|---:|
| do nothing (leave text as typed) | 32.7% | 0.0% | 100.0% |
| dictionary only (unseen words unchanged) | 67.9% | 52.5% | 99.4% |
| dictionary + character context | 89.3% | 88.0% | 91.8% |
| **+ Russian-word guard (qazfix default)** | **89.8%** | **87.9%** | **93.7%** |
| + vowel harmony (experimental `--harmony`) | 89.5% | 87.6% | 93.6% |

Reproduce:

```bash
git clone https://github.com/UniversalDependencies/UD_Kazakh-KTB
python scripts/prepare_ud.py UD_Kazakh-KTB data/          # → data/ud_train.txt, data/ud_test.txt
curl -LO https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/kk/kk_full.txt
python scripts/russian_words.py 30000 > russian.txt       # needs: pip install wordfreq
python scripts/compare.py kk_full.txt data/ud_train.txt --test data/ud_test.txt --russian russian.txt
```

**What this tells us:**
- A dictionary alone fails because Kazakh is agglutinative: endless inflected forms
  (`тілінде`, `тіліміздегі`…) never appear in any word list. Deciding each letter from its
  neighbours is what takes accuracy from 68% to 89%.
- My vowel-harmony idea (front/back vowels) sounded good but **slightly hurt** on this data.
  It's off by default until a bigger corpus says otherwise.
- **The starter model is small** (about 6,000 words, from subtitles and treebank text). Most
  remaining errors are names it has never seen: `Бекболат → Беқболат`, `Шолпан`, `Шымкент`.
  Training on Kazakh Wikipedia is the next step (see below).

## Real-world check: chat messages

Formal text is the easy case. Running qazfix on a real WhatsApp chat (typed casually, mixing Kazakh
and Russian) exposed problems the treebank test could not:

| found in real chat | example | status |
|---|---|---|
| words already typed correctly got changed | `қазір → қәзір` | **fixed**: words containing a Kazakh letter are left alone |
| many people type **і as ы**, not и | `негызы`, `озым`, `быреуы` | **fixed**: ы→і is tried against the word table |
| chat words became real but wrong words | `ок → оқ`, `хахаха → хаһаһа` | **fixed**: chat words and laughter are left alone |
| Russian words with Kazakh endings | `списокта → спісоқта` | open |
| shorthand with dropped vowels | `бугн → бүғн` | open (should be left alone) |

On the held-out test text typed the chat way (і as ы), handling ы→і raised accuracy from
**65.7% to 76.1%**, with no change on normally typed text. To measure qazfix on your own messages,
see `scripts/pair_eval.py` (keep chat files out of git).

## How it works

1. **Seen word:** pick its most frequent spelling (`казак` → `қазақ`).
2. **Common Russian word:** leave it unchanged (Kazakh speakers mix in Russian all the time).
3. **Unseen word:** decide each ambiguous letter from up to 4 letters on each side, backing off
   to smaller windows. This handles inflected forms the dictionary has never seen.

Details: [SPEC.md](SPEC.md).

## Train a stronger model

```bash
pip install "qazfix[build]" datasets
python scripts/wikipedia_text.py kkwiki.txt              # download Kazakh Wikipedia as text
python scripts/russian_words.py 30000 > russian.txt
qazfix build kkwiki.txt -o model.json.gz --russian russian.txt
qazfix eval ud_test.txt --model model.json.gz            # always measure on held-out text
```

Any plain Kazakh text works as a corpus, as do `word count` frequency lists.

## Roadmap

- [x] v0.1: library, CLI, character-context model, Russian guard, honest evaluation
- [x] v0.1.1: fixes from real chat testing (ы typed for і, chat words, already-correct words)
- [x] v0.2: keyboard mode: ranked suggestions, confident auto-correct, completion
- [ ] JavaScript port (`qazfix.js`) with a Python-vs-JS cross-check test
- [ ] Suggestion bar in the Kazakh Adaptive Keyboard web app
- [ ] Hand-checked accuracy on real chat messages
- [ ] Leave Russian words with Kazakh endings alone (`списокта`, `этажго`)
- [ ] Train on Kazakh Wikipedia and publish before/after numbers
- [ ] Two-word context for true ambiguities (`казак`/`қазақ`, `он`/`өң`)
- [ ] Browser demo on GitHub Pages
- [ ] Android keyboard (same model file)

## License

Code: MIT. Bundled model data: CC BY-SA 4.0, see [DATA_LICENSE.md](DATA_LICENSE.md) for sources.
