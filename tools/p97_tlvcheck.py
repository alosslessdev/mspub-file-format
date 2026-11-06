"""Cross-check the Publisher block-length table against the 95/97/98 corpora.

The table below is `MSPUBParser::getBlockDataLength`
(ref/libmspub/src/lib/MSPUBParser.cpp:210).  It is the table of the shared
Publisher "Quill"/Contents block parser.  NOTE: this parser does not appear to
be reachable from the Publisher 95/97/98 chunk payloads -- see
notes/p97/slices/tlv_table.md.  The tool therefore doubles as a negative
control: if the table matched the 95/97 payloads, walking a chunk from the
correct prologue would terminate exactly at the end of the payload far more
often than by chance.

Block framing: {u8 id, u8 type, payload}; the payload width is implied by
`type`.  Variable-length types carry a u32 little-endian length INCLUDING the
four length bytes (libmspub reads `length - 4` data bytes).

Usage:
    python p97_tlvcheck.py p97/x p95/x
    python p97_tlvcheck.py p95/x --table --markers 0x22,0x14
    python p97_tlvcheck.py p97/x --max-prologue 64 --min-blocks 2
"""
from __future__ import annotations

import argparse
import collections
import glob
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

# type -> payload byte length; None = u32 length prefix (count includes the 4 bytes).
BLOCK_LEN = {
    0x00: 0,     # DUMMY
    0x05: 0,
    0x07: 2,
    0x08: 0,
    0x0A: 0,
    0x10: 2,
    0x12: 2,
    0x18: 2,
    0x1A: 2,
    0x20: 4,
    0x22: 4,
    0x28: 8,
    0x38: 16,
    0x48: 24,
    0x58: 4,
    0x68: 4,
    0x70: 4,
    0x78: 0,     # DUMMY (libmspub)
    0x80: None,
    0x82: None,
    0x88: None,  # GENERAL_CONTAINER
    0x8A: None,
    0x90: None,
    0x98: None,
    0xA0: None,
    0xC0: None,  # STRING_CONTAINER
    0xB8: 4,
}

VAR_LEN = {t for t, v in BLOCK_LEN.items() if v is None}
KNOWN = set(BLOCK_LEN)


class Walk:
    __slots__ = ("blocks", "consumed", "known", "var", "bad", "zero")

    def __init__(self, blocks, consumed, known, var, bad, zero=0):
        self.blocks = blocks
        self.consumed = consumed   # bytes consumed from the walk start
        self.known = known         # blocks whose type is in BLOCK_LEN
        self.var = var             # variable-length blocks seen
        self.bad = bad             # True if a block ran past the payload end
        self.zero = zero           # blocks with a zero-byte payload


def walk(payload: bytes, start: int, unknown_len0: bool = False) -> Walk:
    """Walk a TLV list from `start` to the end of `payload`.

    With `unknown_len0` an unknown type is treated as len 0 (libmspub's default
    branch) so the walk always makes progress.  Otherwise an unknown type ends
    the walk in the `bad` state -- that is the only useful test of whether the
    table explains a payload: with the lenient policy every even-length payload
    "terminates exactly", which is a tautology, not evidence.
    """
    rel = start
    n = len(payload)
    blocks = known = var = zero = 0
    while rel + 2 <= n:
        btype = payload[rel + 1]
        blocks += 1
        if btype in KNOWN:
            known += 1
        elif not unknown_len0:
            return Walk(blocks, rel - start, known, var, True, zero)
        ln = BLOCK_LEN.get(btype, 0)
        if ln == 0:
            zero += 1
        if ln is None:
            var += 1
            if rel + 6 > n:
                return Walk(blocks, rel - start, known, var, True, zero)
            tot = struct.unpack_from("<I", payload, rel + 2)[0]
            if tot < 4 or rel + 2 + tot > n:
                return Walk(blocks, rel - start, known, var, True, zero)
            rel += 2 + tot
        else:
            if rel + 2 + ln > n:
                return Walk(blocks, rel - start, known, var, True, zero)
            rel += 2 + ln
    return Walk(blocks, rel - start, known, var, rel != n, zero)


def check_chunk(payload: bytes, max_prologue: int, min_blocks: int,
                unknown_len0: bool = False):
    """Return (best_start, best_walk) or (None, None) if nothing terminates exactly."""
    best = None
    for start in range(min(max_prologue, len(payload)) + 1):
        w = walk(payload, start, unknown_len0)
        if w.bad or w.blocks < min_blocks:
            continue
        if start + w.consumed != len(payload):
            continue
        # prefer the shortest prologue (largest block count) that terminates
        score = (w.blocks, -start)
        if best is None or score > best[0]:
            best = (score, start, w)
    if best is None:
        return None, None
    return best[1], best[2]



# Groups of block types that share a payload length in BLOCK_LEN.  A compiled
# length table (byte/short/dword array indexed by type) must show these three
# groups as constant runs and must distinguish all six probe values.
_GROUPS = ([0x05, 0x08, 0x0A, 0x78], [0x10, 0x12, 0x18, 0x1A, 0x07],
           [0x20, 0x22, 0x58, 0x68, 0x70, 0xB8], [0x28], [0x38], [0x48])


def scan_binary_for_table(paths):
    """Search PE images for a 256-entry array encoding BLOCK_LEN.

    Returns a list of (path, offset, width, values).  A hit means the binary
    really contains the table as data; no hit means the table is either absent
    or implemented as code (a switch), which then has to be found by
    disassembly.
    """
    try:
        import numpy as np
    except ImportError:
        print("numpy required for --scan-binaries")
        return []
    hits = []
    for path in paths:
        with open(path, "rb") as fh:
            blob = fh.read()
        arr = np.frombuffer(blob, dtype=np.uint8)
        for width, dtype in ((1, np.uint8), (2, np.uint16), (4, np.uint32)):
            n = len(arr) // width - 256
            if n <= 0:
                continue
            vals = np.frombuffer(blob, dtype=dtype, count=n + 256)
            ok = np.ones(n, bool)
            for grp in _GROUPS:
                base = vals[grp[0]:grp[0] + n]
                for k in grp[1:]:
                    ok &= (vals[k:k + n] == base)
            for idx in np.nonzero(ok)[0]:
                v = [int(vals[idx + k]) for k in (0x05, 0x10, 0x20, 0x28, 0x38, 0x48)]
                if len(set(v)) == 6:
                    hits.append((path, int(idx) * width, width, v))
    return hits



def scan_code_for_switch(paths, window=600):
    """Search for a `cmp reg, imm` cluster that could be the length switch.

    Linear sweep with skipdata over the raw file (no section parsing), so data
    bytes are swept too -- the test is therefore *permissive*: a function that
    really compares a byte against the fifteen table types would show up as a
    cluster of 15 distinct immediates within `window` bytes.  Any result below
    that threshold can be reported as "no such switch exists in the image".
    """
    try:
        import capstone
    except ImportError:
        print("capstone required for --scan-code")
        return
    table_types = sorted(BLOCK_LEN)
    try:
        import pefile
    except ImportError:
        pefile = None
    for path in paths:
        with open(path, "rb") as fh:
            blob = fh.read()
        # sweep code sections only -- a raw-file sweep hits data tables and
        # produces meaningless "clusters"
        regions = []
        if pefile is not None:
            pe = pefile.PE(path, fast_load=True)
            for sct in pe.sections:
                if sct.Name.startswith(b".text") or sct.Name.startswith(b".code"):
                    regions.append((blob[sct.PointerToRawData:
                                         sct.PointerToRawData + sct.Misc_VirtualSize],
                                    pe.OPTIONAL_HEADER.ImageBase + sct.VirtualAddress))
        if not regions:
            regions = [(blob, 0)]
        md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        md.skipdata = True
        events = []
        for code, base in regions:
            for ins in md.disasm(code, base):
                if ins.mnemonic != "cmp":
                    continue
                op = ins.op_str.split(",")[-1].strip()
                if not op.startswith("0x"):
                    continue
                try:
                    v = int(op, 16)
                except ValueError:
                    continue
                if v in BLOCK_LEN:
                    events.append((ins.address, v))
        events.sort()
        best = (0, 0, [])
        for i, (addr, v) in enumerate(events):
            seen = {v}
            j = i
            while j + 1 < len(events) and events[j + 1][0] - addr <= window:
                j += 1
                seen.add(events[j][1])
            if len(seen) > best[0]:
                best = (len(seen), addr, sorted(seen))
        print("%-24s text cmp-imm %5d  best cluster %2d/%d at 0x%x  %s"
              % (os.path.basename(path), len(events), best[0], len(table_types),
                 best[1], ["%#04x" % x for x in best[2]]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpora", nargs="*")
    ap.add_argument("--max-prologue", type=int, default=64)
    ap.add_argument("--min-blocks", type=int, default=2)
    ap.add_argument("--markers", default=None,
                    help="comma separated chunk type markers (hex), default: all")
    ap.add_argument("--null-trials", type=int, default=2,
                    help="random-byte control per marker (0 disables)")
    ap.add_argument("--unknown-len0", action="store_true",
                    help="treat unknown block types as zero length (libmspub default)")
    ap.add_argument("--table", action="store_true", help="print the length table and exit")
    ap.add_argument("--scan-code", nargs="+", metavar="DIR",
                    help="search binaries for a 15-way cmp-imm switch (capstone)")
    ap.add_argument("--scan-binaries", nargs="+", metavar="DIR",
                    help="search every file under DIR for a compiled copy of the table")
    a = ap.parse_args()

    if a.scan_code:
        paths = []
        for d in a.scan_code:
            if os.path.isdir(d):
                paths += sorted(os.path.join(d, x) for x in os.listdir(d)
                                if os.path.isfile(os.path.join(d, x)))
            else:
                paths.append(d)
        scan_code_for_switch(paths)
        return 0

    if a.scan_binaries:
        paths = []
        for d in a.scan_binaries:
            if os.path.isdir(d):
                paths += sorted(os.path.join(d, x) for x in os.listdir(d)
                                if os.path.isfile(os.path.join(d, x)))
            else:
                paths.append(d)
        hits = scan_binary_for_table(paths)
        print("scanned %d files, %d table hits" % (len(paths), len(hits)))
        for path, off, width, vals in hits[:20]:
            print("  %s @0x%x width=%d groups=%s" % (path, off, width, vals))
        return 0

    if a.table:
        for t in sorted(BLOCK_LEN):
            v = BLOCK_LEN[t]
            print("%#04x  %s" % (t, "var (u32 prefix)" if v is None else "%d bytes" % v))
        return 0

    wanted = ({int(x, 16) for x in a.markers.split(",")} if a.markers else None)
    per_type = collections.defaultdict(list)
    files = 0
    for corpus in a.corpora:
        paths = sorted(glob.glob(os.path.join(corpus, "**", "*.PUB"), recursive=True))
        paths += sorted(glob.glob(os.path.join(corpus, "**", "*.pub"), recursive=True))
        for path in paths:
            try:
                doc = pubcore.parse_contents(path)
            except Exception:
                continue
            files += 1
            for c in doc.chunks:
                if wanted is not None and c.type_marker not in wanted:
                    continue
                per_type[c.type_marker].append(c)

    print("corpora: %s" % ", ".join(a.corpora))
    print("files parsed: %d  chunk markers: %d  max prologue: %d  min blocks: %d  unknown->%s"
          % (files, len(per_type), a.max_prologue, a.min_blocks,
             "len0" if a.unknown_len0 else "fail"))
    print()
    print("%-8s %7s %8s %6s %9s %8s %6s %7s %6s %10s"
          % ("marker", "      n", "  exact", "  frac", " prologue", "blocks", " var",
             " pl%", "  nd", "  null"))
    rows = []
    rng = random.Random(0x97)
    for tm in sorted(per_type):
        chunks = per_type[tm]
        n = len(chunks)
        exact = 0
        best_p = collections.Counter()
        nblocks = var = nzero = nd = 0
        for c in chunks:
            p, w = check_chunk(c.data, a.max_prologue, a.min_blocks, a.unknown_len0)
            if p is not None:
                exact += 1
                best_p[p] += 1
                nblocks += w.blocks
                var += w.var
                nzero += w.zero
                if w.blocks and (w.blocks - w.zero) * 2 >= w.blocks:
                    nd += 1
        # null model: same payload lengths, uniformly random bytes
        null = 0.0
        if a.null_trials:
            sample = chunks if n <= 200 else rng.sample(chunks, 200)
            hit = tried = 0
            for c in sample:
                for _ in range(a.null_trials):
                    buf = bytes(rng.randrange(256) for _ in range(len(c.data)))
                    p, _w = check_chunk(buf, a.max_prologue, a.min_blocks, a.unknown_len0)
                    hit += p is not None
                    tried += 1
            null = 100.0 * hit / tried if tried else 0.0
        top_p = best_p.most_common(1)[0][0] if best_p else -1
        pl = 100.0 * (nblocks - nzero) / nblocks if nblocks else 0.0
        rows.append((tm, n, exact, exact / n, top_p, nblocks, var, pl, nd, null))
    rows.sort(key=lambda r: (-r[8], -r[3], -r[1]))
    for tm, n, exact, frac, top_p, nblocks, var, pl, nd, null in rows:
        print("%#08x %7d %8d %5.1f%% %9s %8d %6d %6.1f%% %6d %9.1f%%"
              % (tm, n, exact, 100 * frac, ("+%d" % top_p) if top_p >= 0 else "-",
                 nblocks, var, pl, nd, null))
    print()
    tot = sum(r[1] for r in rows)
    tot_exact = sum(r[2] for r in rows)
    tot_nd = sum(r[8] for r in rows)
    print("TOTAL chunks %d, exact-terminating %d (%.1f%%), non-degenerate %d (%.2f%%)"
          % (tot, tot_exact, 100.0 * tot_exact / tot if tot else 0.0,
             tot_nd, 100.0 * tot_nd / tot if tot else 0.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
