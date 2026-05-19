#!/usr/bin/env python3
"""
Build the full Russian accent dictionary from ruaccent's source files.

Output schema: {"<input_word>": "<output_with_U+0301>"}
- All Zaliznyak inflected forms (no length cut-off).
- Homographs include the first ruaccent variant as a deterministic default.
- ё-restoration: 'елка' -> 'ё́лка', 'трехлетний' -> 'трёхле́тний', etc.
  Pass 1: yo_words.json from ruaccent.
  Pass 2 (NEW): yoficator.dic from unabashed/yoficator. ~58K curated
    "safe" e→ё pairs covering proper names and -ьё forms that ruaccent's
    yo_words.json misses (e.g. Аксёнов, битьё, бытьё). Two effects:
      - Adds missing e-form keys where the dict had no entry at all.
      - Overwrites e-form entries whose stress points at the e-variant
        when the ё-variant exists in accents.json — those are cases
        where ruaccent decided the e-spelling was authoritative but
        the word actually carries ё.
    yoficator is "conservative": it only ships pairs where no homograph
    exists, so the overwrites are always safe.

Source files (gunzip these from https://huggingface.co/ruaccent/accentuator/tree/main/dictionary
into /tmp/ruaccent/):
- accents.json       (~167 MB raw, 3.19M entries)
- omographs.json     (~1.4 MB)
- yo_words.json      (~4.4 MB)

yoficator.dic is shipped in this build directory (see ./yoficator.dic).
Original source: https://github.com/unabashed/yoficator (BSD-style license).

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

    # Pass 2: yoficator.dic augmentation. Format is "e_form:yo_form" per line,
    # one per declension. Use it to (a) add e-form keys we don't yet have, and
    # (b) overwrite e-form keys whose existing stress targets the e-spelling
    # when the ё-spelling exists in accents.json. yoficator is conservative
    # (no-homograph pairs only), so both operations are safe.
    yof_path = os.path.join(os.path.dirname(__file__) or ".", "yoficator.dic")
    if os.path.exists(yof_path):
        added = 0
        overwritten = 0
        no_stress = 0
        with open(yof_path, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n").rstrip("\r")
                if not line or ":" not in line:
                    continue
                e_form, yo_form = line.split(":", 1)
                if not e_form or not yo_form:
                    continue
                # The ё-form's stressed entry: prefer what's already in result
                # (after pass 1) so we inherit any homograph-picked variant;
                # fall back to a direct accents lookup so we cover ё-forms
                # whose stressed entry was never copied into result above.
                stressed = result.get(yo_form)
                if stressed is None:
                    raw = accents.get(yo_form)
                    if raw is None or "+" not in raw:
                        no_stress += 1
                        continue
                    if yo_form in omographs:
                        variants = omographs[yo_form]
                        if isinstance(variants, list) and variants:
                            raw = variants[0]
                    stressed = convert(raw)
                existing = result.get(e_form)
                if existing is None:
                    added += 1
                elif existing != stressed:
                    overwritten += 1
                result[e_form] = stressed
        print(f"  yoficator augmentation: +{added:,} new e-forms, "
              f"{overwritten:,} overwritten with ё-variant, "
              f"{no_stress:,} skipped (no stress for ё-form)")
    else:
        print(f"  WARN: yoficator.dic not found at {yof_path}, skipping pass 2")

    out_path = os.path.join(os.path.dirname(__file__) or ".", "russian_accents_full.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    sz = os.path.getsize(out_path) / 1024 / 1024
    print(f"{out_path}: {len(result):,} entries, {sz:.1f} MB")


if __name__ == "__main__":
    main()
