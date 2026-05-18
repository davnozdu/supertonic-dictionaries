# Supertonic dictionaries

Pre-built pronunciation dictionaries for the [Supertonic Android](https://github.com/davnozdu/supertonic-android) fork. Each file is a flat JSON object of the form `{"слово": "сло́во"}`, where the value carries combining acute accents (`U+0301`) after stressed vowels — the format the in-app **Lexicon → Download accent dictionary** flow expects.

## Russian (release [`russian-v1.0`](https://github.com/davnozdu/supertonic-dictionaries/releases/tag/russian-v1.0))

| File | Size | Entries | Heap | Coverage |
|---|---|---|---|---|
| `russian_accents_full.json` | 165 MB | 3 263 003 | ~500 MB | Everything: all Zaliznyak inflected forms, homographs, ё-restoration, names |
| `russian_accents.json` | 36 MB | 961 968 | ~150 MB | Words ≤ 9 chars, homographs skipped |
| `russian_accents_compact.json` | 21 MB | 615 365 | ~85 MB | Words ≤ 8 chars, homographs skipped |

Source: derived from [`ruaccent/accentuator`](https://huggingface.co/ruaccent/accentuator) (built on top of A. A. Zaliznyak's grammar dictionary). Conversion script in [`build/`](build/).

### Homograph defaults

The full dictionary picks the **first** stress variant ruaccent lists. That's the dictionary headword, not necessarily the most frequent reading — for words like `замо́к`/`за́мок` the model still benefits from a Lexicon override on whichever side the user reads more often.

### ё-restoration

Words spelled without ё (`елка`, `ежик`, `трехлетний`) resolve to the correct ё-form with stress (`ё́лка`, `ё́жик`, `трёхле́тний`) in one lookup.

## Other languages

Not provided yet. If you have a stress dictionary for any of the 31 Supertonic-3 languages in the `{"word": "wórd"}` shape with `U+0301`-style diacritics — open an issue or PR.
