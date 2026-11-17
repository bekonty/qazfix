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
- [ ] Train on Kazakh Wikipedia and publish before/after numbers
- [ ] Two-word context for true ambiguities (`казак`/`қазақ`, `он`/`өң`)
- [ ] Browser demo on GitHub Pages
- [ ] Browser extension and keyboard integration

## License

Code: MIT. Bundled model data: CC BY-SA 4.0, see [DATA_LICENSE.md](DATA_LICENSE.md) for sources.
