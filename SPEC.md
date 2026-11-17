# qazfix: Specification (v0.1)

## Problem

Kazakh has nine letters that Russian keyboards lack: **ә ғ қ ң ө ұ ү і һ**.
People routinely type the nearest Russian letter instead (қ→к, і→и, ұ/ү→у…).
The result is readable to humans but breaks search, spell-checking,
text-to-speech and language models. qazfix restores the intended letters.

## Non-goals

- Not a spell-checker: typos other than missing Kazakh letters are left alone.
- Not a transliterator: Latin-script Kazakh is left untouched (other tools do this).
- Never changes a letter the user already typed as a Kazakh letter.

## The mapping

| Kazakh letter | typed as |
|---|---|
| ә | а |
| ғ | г |
| қ | к |
| ң | н |
| ө | о |
| ұ, ү | у |
| і | и (or a Latin `i`) |
| һ | х |

Restoration is a **one-to-one character mapping**, so length, case and
punctuation can always be preserved exactly.

## Algorithm

For each Cyrillic word (lowercased; case is re-applied per character after):

0. **Leave alone**: words already containing a Kazakh letter (the writer is typing
   properly), chat words (`ок`, `окок`, `ия`) and laughter (`хахаха`).
1. **Word table.** If the stripped word was seen in training, output its most
   frequent original spelling (e.g. `казак` → `қазақ`, which beats the rarer
   Russian-origin `казак` "Cossack").
1b. **ы typed for і.** Many people type і as ы (`быз` for біз). If the word is
   unknown, try turning ы into і and accept only word-table hits.
2. **Russian guard.** Else, if it is a common Russian word, leave it unchanged.
   Kazakh speakers mix Russian in constantly ("ертең встреча бар ма?").
3. **Character context.** Else, decide each ambiguous letter from up to 4
   letters on each side (with `^`/`$` word boundaries), backing off to smaller
   windows until a context seen at least twice in training is found. Counts are
   over word *types*, not tokens, which generalises better to unseen
   inflections. Kazakh is agglutinative, so most words in real text are
   inflected forms no dictionary contains; this step handles them.

Experimental (`qazfix build --harmony`): add the word's vowel-harmony class
(front if `е` survives stripping, back if `ы` does) to the context. It did not
help on the starter data (see README) and is off by default.

## Evaluation

`qazfix eval FILE` takes correctly written Kazakh text, strips it, restores it,
and counts only words that contain an ambiguous letter after stripping (the
others are trivially correct). It reports:

- **word accuracy**: restored word equals the original;
- **needed a Kazakh letter**: share of words with ә/ғ/… that were restored;
- **already correct**: share of plain words left alone (false-change check).

Test text must be held out from training, split by source document.

## Roadmap

1. Train on Kazakh Wikipedia (`scripts/wikipedia_text.py`); re-test `--harmony`.
2. Two-word context to settle real ambiguities (`он` "ten" vs `өң`, `казак` vs `қазақ`).
3. Browser demo on GitHub Pages (same model, ported to JavaScript).
4. Browser extension / keyboard integration.
