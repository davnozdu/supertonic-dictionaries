#!/usr/bin/env python3
"""
Build the full Russian accent dictionary from ruaccent's source files.

Output schema: {"<input_word>": "<output_with_U+0301>"}
- All Zaliznyak inflected forms (no length cut-off).
- Homographs include the first ruaccent variant as a deterministic default.
- ё-restoration: 'елка' -> 'ё́лка', 'трехлетний' -> 'трёхле́тний', etc.

Source files (gunzip these from https://huggingface.co/ruaccent/accentuator/tree/main/dictionary
into /tmp/ruaccent/):
- accents.json       (~167 MB raw, 3.19M entries)
- omographs.json     (~1.4 MB)
- yo_words.json      (~4.4 MB)

Usage:
    python3 build_full.py
Writes russian_accents_full.json next to this script.
"""
import json
import os
import sys

ACUTE = "́"


def convert(val: str) -> str:
    """Move ruaccent's '+' from before the stressed vowel to a combining acute after it."""
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


def main() -> None:
    src_root = "/tmp/ruaccent"
    accents_path = os.path.join(src_root, "accents.json")
    omographs_path = os.path.join(src_root, "omographs.json")
    yo_path = os.path.join(src_root, "yo_words.json")
    for p in (accents_path, omographs_path, yo_path):
        if not os.path.exists(p):
            sys.exit(f"Missing {p} — see README for the curl + gunzip commands.")

    with open(accents_path, encoding="utf-8") as f:
        accents = json.load(f)
    with open(omographs_path, encoding="utf-8") as f:
        omographs = json.load(f)
    with open(yo_path, encoding="utf-8") as f:
        yo_words = json.load(f)

    result = {}
    for key, val in accents.items():
        if "+" not in val:
            continue
        if key in omographs:
            variants = omographs[key]
            if isinstance(variants, list) and variants:
                val = variants[0]
        result[key] = convert(val)

    for plain, with_yo in yo_words.items():
        # If the ё-version is in the stressed map, route the no-ё spelling to it;
        # otherwise fall back to the ё-form unchanged (still better than nothing).
        result[plain] = result.get(with_yo, with_yo)

    out_path = os.path.join(os.path.dirname(__file__) or ".", "russian_accents_full.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    sz = os.path.getsize(out_path) / 1024 / 1024
    print(f"{out_path}: {len(result):,} entries, {sz:.1f} MB")


if __name__ == "__main__":
    main()
