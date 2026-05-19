#!/usr/bin/env python3
"""
Converts a JSON accent dictionary into the .sacc binary format
that the Android app can mmap and binary-search without loading
the whole thing into RAM.

File layout (little-endian):

    Header (28 bytes):
        0:  magic           u8[4]  = b"SACC"
        4:  version         u32    = 1
        8:  entry_count     u32
        12: offsets_offset  u64
        20: data_offset     u64

    Offsets table (entry_count * 4 bytes):
        offsets_offset + i*4 -> u32 offset of entry i in the data section
        (offsets are relative to data_offset, so the file can be < 4 GB)

    Data section (entry_count entries, sorted by lowercased UTF-8 key):
        u16 key_len        (number of UTF-8 bytes)
        u16 value_len      (number of UTF-8 bytes)
        bytes key           (key_len bytes)
        bytes value         (value_len bytes)

The Android side mmaps the whole file via FileChannel.map and does
binary search on the offsets table. Memory usage is bounded by the
OS page cache (~10-20 MB hot working set), not the file size.

Usage:
    python build_binary.py <input.json> <output.sacc>
"""
import json
import os
import struct
import sys


MAGIC = b"SACC"
VERSION = 1
HEADER_FMT = "<4sIIQQ"
HEADER_SIZE = struct.calcsize(HEADER_FMT)  # 28
ENTRY_HEADER_FMT = "<HH"
ENTRY_HEADER_SIZE = struct.calcsize(ENTRY_HEADER_FMT)  # 4


def convert(json_path: str, bin_path: str) -> None:
    print(f"Reading {json_path}...", flush=True)
    with open(json_path, "rb") as f:
        raw = f.read()
    data = json.loads(raw)
    print(f"  parsed {len(data):,} entries from JSON ({len(raw) / 1_048_576:.1f} MB)", flush=True)

    # Lowercase keys (matches AccentDictionaryManager.apply which lowercases
    # at lookup time) and sort by the UTF-8 byte representation. The Android
    # binary search compares UTF-8 byte-by-byte against the query, so the
    # sort key MUST be the byte order, not the codepoint order.
    print("  lowercasing and sorting by UTF-8 bytes...", flush=True)
    pairs: list[tuple[bytes, bytes]] = []
    for key, value in data.items():
        if not key or not value:
            continue
        kb = key.lower().encode("utf-8")
        vb = value.encode("utf-8")
        if len(kb) > 0xFFFF or len(vb) > 0xFFFF:
            # u16 cap. We don't expect anywhere near 64 KB for a single word.
            print(f"  WARN: oversize entry skipped ({len(kb)} / {len(vb)})", flush=True)
            continue
        pairs.append((kb, vb))
    pairs.sort(key=lambda kv: kv[0])

    # Dedupe sorted-adjacent identical keys, keeping the first occurrence.
    deduped: list[tuple[bytes, bytes]] = []
    last_key = None
    for kb, vb in pairs:
        if kb == last_key:
            continue
        deduped.append((kb, vb))
        last_key = kb
    pairs = deduped

    count = len(pairs)
    print(f"  unique entries: {count:,}", flush=True)

    # Build the data section, tracking offsets per entry.
    print("  packing data section...", flush=True)
    data_buf = bytearray()
    offsets: list[int] = []
    for kb, vb in pairs:
        offsets.append(len(data_buf))
        data_buf += struct.pack(ENTRY_HEADER_FMT, len(kb), len(vb))
        data_buf += kb
        data_buf += vb

    offsets_offset = HEADER_SIZE
    data_offset = HEADER_SIZE + count * 4

    # Sanity: every offset must fit in u32 (data section < 4 GB).
    if data_buf and offsets[-1] >= 2**32:
        raise OverflowError(
            f"Data section too large: last offset {offsets[-1]} >= 2^32 "
            f"({len(data_buf) / 1_073_741_824:.2f} GiB)"
        )

    print(f"  writing {bin_path}...", flush=True)
    with open(bin_path, "wb") as f:
        f.write(struct.pack(HEADER_FMT, MAGIC, VERSION, count, offsets_offset, data_offset))
        f.write(struct.pack(f"<{count}I", *offsets))
        f.write(data_buf)

    out_size = os.path.getsize(bin_path)
    print(
        f"  wrote {out_size / 1_048_576:.1f} MB "
        f"(vs JSON {len(raw) / 1_048_576:.1f} MB, ratio {out_size / len(raw):.2f})",
        flush=True,
    )


def verify(bin_path: str, sample_keys: list[str]) -> None:
    """Quick sanity check: re-read the binary and look up a few keys via
    in-memory binary search. Doesn't mmap (that's the Android job)."""
    with open(bin_path, "rb") as f:
        buf = f.read()
    magic, version, count, off_offsets, off_data = struct.unpack_from(HEADER_FMT, buf, 0)
    assert magic == MAGIC, f"bad magic: {magic!r}"
    assert version == VERSION, f"bad version: {version}"
    print(f"  header OK: {count:,} entries, offsets@{off_offsets}, data@{off_data}", flush=True)

    def entry_at(i: int) -> tuple[bytes, bytes]:
        rel = struct.unpack_from("<I", buf, off_offsets + i * 4)[0]
        absp = off_data + rel
        key_len, val_len = struct.unpack_from(ENTRY_HEADER_FMT, buf, absp)
        kb = buf[absp + 4 : absp + 4 + key_len]
        vb = buf[absp + 4 + key_len : absp + 4 + key_len + val_len]
        return kb, vb

    for sk in sample_keys:
        target = sk.lower().encode("utf-8")
        lo, hi = 0, count - 1
        result = None
        while lo <= hi:
            mid = (lo + hi) // 2
            kb, vb = entry_at(mid)
            if kb < target:
                lo = mid + 1
            elif kb > target:
                hi = mid - 1
            else:
                result = vb.decode("utf-8")
                break
        print(f"  {sk!r:20s} -> {result!r}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
    # Smoke test
    verify(sys.argv[2], ["Москва", "правило", "хорошо", "нет_такого_слова"])
