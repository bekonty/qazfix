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

For each Cyrillic word (lowercased; case is put back afterwards, letter by letter, or for the whole
word when a vowel was added):

0. **Leave alone**: words already containing a Kazakh letter (the writer is typing properly),
   chat words (`ок`, `окок`, `ия`) and laughter (`хахаха`).
1. **Word table.** If the stripped word was seen in training, output its most frequent valid
   spelling. Where a key has dictionary spellings, only those are kept (`кәзір` loses to `қазір`
   when the corpus has both).
2. **ы typed for і.** Many people type і as ы (`быз` for біз). If the word is unknown, try ы→і and
   accept only word-table hits. Skipped for real ы-words: a known stem + ending with no front
   vowel е (`кыргызды` = қырғыз + ды).
3. **Russian guard.** A common Russian word is left unchanged. A Russian stem + Kazakh ending
   (`списокта`) keeps the Russian part; only the ending can change.
4. **Dropped-vowel shorthand.** If the word is not valid (not in the table, not stem + ending),
   insert one, then two, ы/і between consonants (the last 6 slots: vowels drop near the end).
   Accept candidates that are table words (scored by frequency) or stem + ending (score 0);
   ties go to the candidate whose restored vowels agree in harmony (`колдаймн` → қолдаймын).
5. **Character context.** Else, decide each ambiguous letter from up to 4 letters on each side
   (with `^`/`$` word boundaries), backing off to smaller windows. Counts are over word *types*
   (corpus words + 1.2M dictionary forms).

**Pruning.** A context is dropped when its best letter equals that of the context it falls back to,
chosen at least 99% of the time. 550k → 39k contexts with no accuracy change.

Experimental (`qazfix build --harmony`): vowel-harmony class in the context. Did not help (see README).

## Evaluation

`qazfix eval FILE` takes correctly written Kazakh text, strips it, restores it,
and counts only words that contain an ambiguous letter after stripping (the
others are trivially correct). It reports:

- **word accuracy**: restored word equals the original;
- **needed a Kazakh letter**: share of words with ә/ғ/… that were restored;
- **already correct**: share of plain words left alone (false-change check).

Test text must be held out from training, split by source document.

## Roadmap

1. Kazakh Wikipedia as a frequency corpus (`scripts/wikipedia_text.py`).
2. Two-word context to settle real ambiguities (`казак` vs `қазақ`, `шукыр`: шүкір or шұқыр).
3. Keyboard integration (Kazakh Adaptive Keyboard, Android).
