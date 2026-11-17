# Data license

The **code** in this repository is MIT licensed (see `LICENSE`).

The bundled **model file** `src/qazfix/data/model.json.gz` (and `web/model.json`, exported from it)
is built from the sources below. Because it includes data from GPL-licensed dictionaries, the
model file as a whole is distributed under the
[GNU GPL version 3](https://www.gnu.org/licenses/gpl-3.0.html). CC BY-SA 4.0 material may be
included in a GPLv3 work (Creative Commons lists GPLv3 as a compatible license).

| Source | Used for | License |
|---|---|---|
| [hunspell-kk](https://github.com/taem/hunspell-kk) (Kazakh hunspell dictionary; A. Lipchansky, A. Mussayeva, OpenOffice Lingucomponent) | 54k stems and suffix rules → 1.16M word forms; word endings | GPL-2.0+ / LGPL-2.1+ / MPL-1.1 (used under GPL-3.0) |
| [apertium-kaz](https://github.com/apertium/apertium-kaz) (Apertium Kazakh morphological transducer) | 17k extra stems, including proper names | GPL-3.0 |
| [FrequencyWords](https://github.com/hermitdave/FrequencyWords) by Hermit Dave, `content/2018/kk/kk_full.txt` (from OpenSubtitles) | Kazakh word frequencies | CC BY-SA 4.0 |
| [UD Kazakh-KTB](https://github.com/UniversalDependencies/UD_Kazakh-KTB) (training half only) | Kazakh words in context | CC BY-SA 4.0 |
| [wordfreq](https://github.com/rspeer/wordfreq) Russian word list (top 30,000) | Russian-word guard | CC BY-SA 4.0 (data) |

The other half of UD Kazakh-KTB is used **only for testing** and is not part of the model.

If you need a model without GPL data, build one from the CC BY-SA sources only (omit `--lexicon`,
`--stems` and `--suffixes` in `qazfix build`); it is less accurate (see README).
