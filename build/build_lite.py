#!/usr/bin/env python3
"""
Build a Lexicon-importable accent dictionary from ruaccent's accents.json.

Usage:
    python3 build_lite.py [MAX_WORD_LEN]   # default 9

Reads /tmp/ruaccent/accents.json, omographs.json and yo_words.json (download
the .gz files from https://huggingface.co/ruaccent/accentuator/tree/main/dictionary
and gunzip them first).

Writes russian_accents.json (or russian_accents_compact.json for MAX_LEN==8)
next to this script.

ё-restoration: yo_words.json maps the no-ё spelling ("елка") to the proper
ё-form ("ёлка"). We route the no-ё key to the ё-form's stressed value, so
"елка" -> "ё́лка" instead of "е́лка". Same logic as build_full.py — without
this, the TTS engine pronounces [e] where it should pronounce [yo].
"""

import json
import os
import sys

ACUTE = "́"  # combining acute accent, placed AFTER the stressed vowel

def convert(val: str) -> str:
    """Move ruaccent's '+' from before the vowel to a combining acute after it."""
    out = []
    i = 0
    while i < len(val):
        c = val[i]
        if c == "+" and i + 1 < len(val):
            out.append(val[i + 1])
            out.append(ACUTE)
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def main(max_len: int) -> None:
    src = "/tmp/ruaccent/accents.json"
    omo = "/tmp/ruaccent/omographs.json"
    yo = "/tmp/ruaccent/yo_words.json"
    for p in (src, omo, yo):
        if not os.path.exists(p):
            sys.exit(
                f"Missing {p} — see README for the curl commands that fetch "
                "the source files from Hugging Face."
            )

    with open(src, encoding="utf-8") as f:
        accents = json.load(f)
    with open(omo, encoding="utf-8") as f:
        omographs = json.load(f)
    with open(yo, encoding="utf-8") as f:
        yo_words = json.load(f)

    result = {}
    for key, val in accents.items():
        if len(key) > max_len:
            continue
        if "+" not in val:
            continue
        # Homographs are deliberately skipped — feeding the model one
        # deterministic stress for words like "замок" or "лиса" was worse
        # than letting it pick from context.
        if key in omographs:
            continue
        result[key] = convert(val)

    # ё-restoration: route the no-ё spelling to the stressed ё-form. The size
    # cap applies to the no-ё key (what the user actually types), not to the
    # ё-form whose stressed value we're stealing.
    for plain, with_yo in yo_words.items():
        if len(plain) > max_len:
            continue
        result[plain] = result.get(with_yo, with_yo)

    out_name = "russian_accents.json" if max_len == 9 else "russian_accents_compact.json"
    out_path = os.path.join(os.path.dirname(__file__) or ".", out_name)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    sz = os.path.getsize(out_path) / 1024 / 1024
    print(f"{out_name}: {len(result):,} entries, {sz:.1f} MB")


if __name__ == "__main__":
    max_len = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    main(max_len)
