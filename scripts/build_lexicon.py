"""Build a large Kazakh word list from open dictionaries (no frequencies, just valid words).

Sources (clone them first; both are on GitHub):
  * hunspell-kk  https://github.com/taem/hunspell-kk        (GPL-2.0+/LGPL-2.1+/MPL-1.1)
      54k stems + suffix rules -> every inflected form the rules allow
  * apertium-kaz https://github.com/apertium/apertium-kaz   (GPL-3.0)
      stems from the morphological dictionary, including many proper names

    python scripts/build_lexicon.py hunspell-kk/kk_KZ.dic hunspell-kk/kk_KZ.aff \
        apertium-kaz/apertium-kaz.kaz.lexc lexicon.txt stems.txt suffixes.txt

Outputs (one lowercase item per line, sorted):
  lexicon.txt   every word form (~1.2M): teaches the character model
  stems.txt     dictionary stems (~71k): go in the word table (keeps the model small)
  suffixes.txt  endings from the hunspell rules: let qazfix tell a real inflected
                word (тіл+дерін) from shorthand with a dropped vowel (бугн)
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

CYRILLIC_WORD = re.compile(r"^[а-яёәғқңөұүһі]+(?:-[а-яёәғқңөұүһі]+)*$")


def read_affixes(aff_path: Path):
    """Hunspell SFX rules: flag -> [(strip, add, condition regex)]."""
    rules = defaultdict(list)
    for line in aff_path.read_text(encoding="utf-8-sig").splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0] == "SFX":
            flag, strip, add, cond = parts[1], parts[2], parts[3], parts[4]
            strip = "" if strip == "0" else strip
            add = "" if add == "0" else add.split("/")[0]
            rules[flag].append((strip, add, re.compile("(?:" + cond + ")$") if cond != "." else None))
    return rules


def expand_hunspell(dic_path: Path, aff_path: Path):
    rules = read_affixes(aff_path)
    lines = dic_path.read_text(encoding="utf-8-sig").splitlines()[1:]  # first line is a count
    for line in lines:
        stem, _, flags = line.strip().partition("/")
        if not stem:
            continue
        yield stem
        for flag in flags:
            for strip, add, cond in rules.get(flag, ()):
                if cond is not None and not cond.search(stem):
                    continue
                if strip and not stem.endswith(strip):
                    continue
                yield (stem[: len(stem) - len(strip)] if strip else stem) + add


def apertium_stems(lexc_path: Path):
    """Surface stems from entries like `бауыр:бауыр N1 ; ! "brother"`."""
    in_lexicon = False
    for raw in lexc_path.read_text(encoding="utf-8").splitlines():
        line = raw.split("!", 1)[0].strip()
        if line.startswith("LEXICON"):
            in_lexicon = line.split()[1] in {"Common", "Proper", "Hardcoded"}
            continue
        if not in_lexicon or not line.endswith(";"):
            continue
        entry = line[:-1].split()[0]
        surface = entry.split(":", 1)[-1] if ":" in entry else entry
        surface = surface.replace("%", "").replace(">", "").replace("<", "")
        yield surface


def stems(dic_path: Path, lexc_path: Path):
    for line in dic_path.read_text(encoding="utf-8-sig").splitlines()[1:]:
        yield line.split("/", 1)[0].strip()
    yield from apertium_stems(lexc_path)


def suffixes(aff_path: Path):
    for rules in read_affixes(aff_path).values():
        for _strip, add, _cond in rules:
            if add:
                yield add


def write(path: str, items) -> int:
    words = sorted({w.lower() for w in items if CYRILLIC_WORD.match(w.lower())})
    Path(path).write_text("\n".join(words) + "\n", encoding="utf-8")
    return len(words)


def main(dic: str, aff: str, lexc: str, out: str, stems_out: str, suffixes_out: str) -> None:
    words = set()
    for w in expand_hunspell(Path(dic), Path(aff)):
        w = w.lower()
        if CYRILLIC_WORD.match(w):
            words.add(w)
    before = len(words)
    for w in apertium_stems(Path(lexc)):
        w = w.lower()
        if CYRILLIC_WORD.match(w):
            words.add(w)
    Path(out).write_text("\n".join(sorted(words)) + "\n", encoding="utf-8")
    print(f"hunspell forms: {before:,}; apertium stems added: {len(words) - before:,}; total {len(words):,}")
    print(f"stems: {write(stems_out, stems(Path(dic), Path(lexc))):,}")
    print(f"suffixes: {write(suffixes_out, suffixes(Path(aff))):,}")


if __name__ == "__main__":
    main(*sys.argv[1:7])
