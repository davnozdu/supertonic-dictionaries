# Supertonic dictionaries

Pre-built pronunciation dictionaries for the [Supertonic Android](https://github.com/davnozdu/supertonic-android) fork. Each entry maps a lowercased word to its stressed form, with combining acute accents (`U+0301`) after stressed vowels — the format the model's text encoder consumes.

Two distribution formats are available for every dictionary:

- **`.json`** — flat object `{"слово": "сло́во"}`. Human-readable, easy to hand-edit, but the whole tree has to be parsed into a HashMap on the Android side. For the 165 MB Full dictionary that means ~390 MB heap and ~5-10 s of parse time.
- **`.sacc`** — purpose-built binary format (Supertonic ACCent dictionary). Sorted-by-key UTF-8 entries indexed by a u32 offsets table, mmap-friendly. The Android app reads it via `FileChannel.map` and serves lookups with binary search straight off the page cache. RAM usage stays at ~10-20 MB hot working set regardless of file size; first synthesis is sub-second instead of ~10 s.

Pick `.sacc` for performance on phones, `.json` if you want to inspect or modify the data.

## Russian (release [`russian-v1.0`](https://github.com/davnozdu/supertonic-dictionaries/releases/tag/russian-v1.0))

| Variant | JSON | Binary (`.sacc`) | Entries | Heap (JSON) | RAM (binary) | Coverage |
|---|---|---|---|---|---|---|
| Full | `russian_accents_full.json` (165 MB) | `russian_accents_full.sacc` (171 MB) | 3 263 003 | ~390 MB | ~10-20 MB | Everything: all Zaliznyak inflected forms, homographs, ё-restoration, names |
| Standard | `russian_accents_max9.json` (36 MB) | `russian_accents_max9.sacc` (38 MB) | 961 968 | ~150 MB | ~5-10 MB | Words ≤ 9 chars, homographs skipped |
| Compact | `russian_accents_max8.json` (21 MB) | `russian_accents_max8.sacc` (22 MB) | 615 365 | ~85 MB | ~3-7 MB | Words ≤ 8 chars, homographs skipped |

Note: the `.sacc` files are *slightly* larger on disk than the `.json` files (~3-6 MB overhead for entry-length headers and the offset table). The win is in-memory and at load time — see the **binary file layout** section below for the format details.

Source: derived from [`ruaccent/accentuator`](https://huggingface.co/ruaccent/accentuator) (built on top of A. A. Zaliznyak's grammar dictionary). Conversion scripts in [`build/`](build/).

### Homograph defaults

The full dictionary picks the **first** stress variant ruaccent lists. That's the dictionary headword, not necessarily the most frequent reading — for words like `замо́к`/`за́мок` the model still benefits from a Lexicon override on whichever side the user reads more often.

### ё-restoration

Words spelled without ё (`елка`, `ежик`, `трехлетний`) resolve to the correct ё-form with stress (`ё́лка`, `ё́жик`, `трёхле́тний`) in one lookup.

## Binary file layout (`.sacc` v1)

Little-endian. Versioned via the header.

```
Header (28 bytes):
  0:  magic           u8[4]  = b"SACC"
  4:  version         u32    = 1
  8:  entry_count     u32
 12:  offsets_offset  u64    = 28
 20:  data_offset     u64    = 28 + entry_count * 4

Offsets table (entry_count × 4 bytes):
  offsets_offset + i*4 -> u32 offset relative to data_offset

Data section (entry_count entries, sorted by lowercased UTF-8 key):
  u16 key_len, u16 value_len, <key_len bytes>, <value_len bytes>
```

To look up a key: lowercase it, encode UTF-8, then binary-search the offsets table comparing bytes against entries at each midpoint. See `build/build_binary.py` for the reference encoder and `app/src/main/java/.../utils/BinaryAccentDictionary.kt` in the Android app for a streaming reader.

## Other languages

Not provided yet. If you have a stress dictionary for any of the 31 Supertonic-3 languages in the `{"word": "wórd"}` shape with `U+0301`-style diacritics — open an issue or PR.
