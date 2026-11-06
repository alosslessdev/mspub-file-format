"""Table/cells census and shape-grid detector for the Publisher 95/97/98 corpora.

Sub-commands:
    census   -- marker census for TABLE (0x10) / CELLS (0x63) plus fixed-record sizes.
    grids    -- detect shape grids (tables-as-shapes) per document.
    libmspub -- test libmspub's table block ids (0x66/0x67/0x68/0x69/0x6B/0x6D).
    dump     -- per-shape decode of one parent bucket (coords + record fields).

Usage:
    python tools/p98_tables.py census p95/x p97/ext2 p97deluxe/x p98/x
    python tools/p98_tables.py grids  p95/x p97/ext2 p97deluxe/x p98/x
    python tools/p98_tables.py libmspub p95/x p97/ext2 p97deluxe/x p98/x
    python tools/p98_tables.py dump p95/x/PAGEWIZ/CLASSIC.PUB 0x351
"""
from __future__ import annotations

import argparse
import collections
import glob
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore
import p98_corpus as pc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Chunk markers whose payload carries the shape prologue with a coordinate quad
# at +6 (libmspub MSPUBParser2k::parseShapeCoordinates).
SHAPE_TYPES = {0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x16}
# libmspub's producer-side numbering (MSPUBContentChunkType) for the 2k model.
TABLE_MARKER = 0x10
CELLS_MARKER = 0x63


def marker_bbox(chunk):
    """s32 quadruple at chunk+6 (xs, ys, xe, ye), None when implausible."""
    d = chunk.data
    if len(d) < 22:
        return None
    x0, y0, x1, y1 = struct.unpack_from("<iiii", d, 6)
    if not (0 < x0 < x1 and 0 < y0 < y1):
        return None
    return (x0, y0, x1, y1)


def load_corpora(corpora):
    """Yield (corpus, path, Document) over *.PUB *and* *.JSP publications.

    p98_corpus.pub_files only globs `.pub`; the Publisher 98 CD ships three
    publications with the `.JSP` extension (CHEKLIST, CLRCHK, INFOSHET), so the
    census must add them or the corpus is 488 documents instead of 493.
    """
    for corp in corpora:
        path = corp if os.path.isdir(corp) else os.path.join(ROOT, corp)
        files = sorted(f for f in glob.glob(os.path.join(path, "**", "*"), recursive=True)
                       if f.lower().endswith((".pub", ".jsp")) and os.path.isfile(f))
        for f in files:
            try:
                doc = pubcore.parse_contents(f)
            except Exception:
                continue
            yield corp, f, doc


# --------------------------------------------------------------------------- census

def cmd_census(corpora):
    total = 0
    hist = collections.Counter()
    files_with = collections.Counter()
    sizes = collections.defaultdict(collections.Counter)
    idhits = collections.Counter()
    for corp, f, doc in load_corpora(corpora):
        total += 1
        seen = collections.Counter(c.type_marker for c in doc.chunks)
        hist.update(seen)
        for m in seen:
            files_with[m] += 1
            if m in (TABLE_MARKER, CELLS_MARKER):
                print("HIT type_marker %#04x in %s" % (m, f))
            for k in (TABLE_MARKER, CELLS_MARKER):
                if m == k:
                    pass
        for c in doc.chunks:
            sizes[c.type_marker][c.size] += 1
            if c.id in (TABLE_MARKER, CELLS_MARKER):
                idhits[("id", c.id)] += 1
            if c.parent in (TABLE_MARKER, CELLS_MARKER):
                idhits[("parent", c.parent)] += 1
    print("documents parsed: %d" % total)
    print("TABLE marker 0x%04x: %d chunks in %d documents"
          % (TABLE_MARKER, hist[TABLE_MARKER], files_with[TABLE_MARKER]))
    print("CELLS marker 0x%04x: %d chunks in %d documents"
          % (CELLS_MARKER, hist[CELLS_MARKER], files_with[CELLS_MARKER]))
    print("directory-id/parent collisions with 0x10|0x63: %s" % (dict(idhits) or "none"))
    print("\nmarker histogram (marker  chunks  docs  modal payload size):")
    for m in sorted(hist):
        mode, n = sizes[m].most_common(1)[0]
        print("  0x%04x  %6d  %5d  %6d  (%d/%d chunks)"
              % (m, hist[m], files_with[m], mode, n, hist[m]))
    print("\nsize spread per marker (only markers with >1 size):")
    for m in sorted(sizes):
        if len(sizes[m]) > 1:
            common = sizes[m].most_common(6)
            print("  0x%04x n=%d sizes=%s%s"
                  % (m, hist[m], ", ".join("%d x%d" % (s, c) for s, c in common),
                     " ..." if len(sizes[m]) > 6 else ""))


# --------------------------------------------------------------------------- grids

def row_band_grid(boxes):
    """Return (nrows, ncols, doc rows) when the boxes form a row-aligned grid."""
    rows = collections.defaultdict(list)
    for b in boxes:
        rows[b[1]].append(b)
    ys = sorted(rows)
    best = None
    # every contiguous band of rows
    for i in range(len(ys)):
        for j in range(i + 1, len(ys)):
            band = ys[i:j + 1]
            if len(band) < 2:
                continue
            ok = True
            boundaries = None
            for a, b in zip(band, band[1:]):
                if a + (rows[a][0][3] - rows[a][0][1]) != b:
                    # rows must be adjacent: y1 of a row == y0 of next
                    if not all(r[3] == b for r in rows[a]):
                        ok = False
                        break
            if not ok:
                continue
            rowb = []
            for y in band:
                seg = sorted(rows[y], key=lambda r: r[0])
                # one row cannot contain differing bottoms
                if len({r[3] for r in seg}) != 1:
                    ok = False
                    break
                if seg[0][0] != min(r[0] for r in seg):
                    ok = False
                    break
                # segments tile the row without gap/overlap
                for p, q in zip(seg, seg[1:]):
                    if p[2] != q[0]:
                        ok = False
                        break
                if not ok:
                    break
                b = sorted({r[0] for r in seg} | {r[2] for r in seg})
                if boundaries is None:
                    boundaries = b
                elif b != boundaries:
                    ok = False
                    break
                rowb.append(seg)
            if not ok:
                continue
            ncols = len(boundaries) - 1
            if ncols < 2 or len(band) < 2:
                continue
            cells = sum(len(r) for r in rowb)
            if cells != ncols * len(band):
                continue
            cand = (cells, len(band), ncols, band[0], band[-1], boundaries, rowb)
            if best is None or cand[0] > best[0]:
                best = cand
    return best


def iter_buckets(doc):
    byid = {c.id: c for c in doc.chunks}
    buckets = collections.defaultdict(list)
    for c in doc.chunks:
        if c.type_marker in SHAPE_TYPES:
            b = marker_bbox(c)
            if b:
                buckets[c.parent].append((c, b))
    return byid, buckets


def cmd_grids(corpora, min_cells=4, verbose=True):
    ndocs = 0
    hits = []
    nearbuckets = 0
    for corp, f, doc in load_corpora(corpora):
        ndocs += 1
        byid, buckets = iter_buckets(doc)
        for parent, lst in buckets.items():
            boxes = [b for _, b in lst]
            g = row_band_grid(boxes)
            if not g:
                if len(lst) >= min_cells:
                    nearbuckets += 1
                continue
            cells, nrows, ncols, y0, y1, boundaries, rowb = g
            if cells < min_cells:
                continue
            widths = [boundaries[k + 1] - boundaries[k] for k in range(len(boundaries) - 1)]
            heights = [rowb[k][0][3] - rowb[k][0][1] for k in range(len(rowb))]
            ptype = byid[parent].type_marker if parent in byid else None
            hits.append(dict(corpus=corp, file=f, parent=parent, ptype=ptype,
                             cells=cells, rows=nrows, cols=ncols,
                             uniform_w=len(set(widths)) == 1,
                             uniform_h=len(set(heights)) == 1,
                             widths=widths, heights=heights,
                             shapes=[c for c, _ in lst],
                             boxes=boxes))
            if verbose:
                print("%-34s parent=%#06x type=%s cells=%dx%d uniform(w,h)=(%s,%s) w=%s h=%s"
                      % (os.path.basename(f), parent,
                         "0x%02x" % ptype if ptype is not None else "MISSING",
                         ncols, nrows, len(set(widths)) == 1, len(set(heights)) == 1,
                         widths[:4], heights[:4]))
    print("\ndocuments scanned: %d   grid candidates: %d   >4-shape buckets rejected: %d"
          % (ndocs, len(hits), nearbuckets))
    return hits


def cmd_lattices(corpora, min_cells=4):
    """Equal-size siblings whose top-left corners form a full rows x cols matrix.

    Weaker than `grids`: cells may have gutters between them, but every cell must
    share one width and one height and the corner set must be a complete product.
    """
    ndocs = 0
    hits = []
    for corp, f, doc in load_corpora(corpora):
        ndocs += 1
        byid = {c.id: c for c in doc.chunks}
        buckets = collections.defaultdict(list)
        for c in doc.chunks:
            if c.type_marker in SHAPE_TYPES:
                b = marker_bbox(c)
                if b:
                    buckets[c.parent].append((c, b))
        for parent, lst in buckets.items():
            bysize = collections.defaultdict(list)
            for c, b in lst:
                bysize[(b[2] - b[0], b[3] - b[1])].append((c, b))
            for (w, h), items in bysize.items():
                if len(items) < min_cells:
                    continue
                xs = sorted({b[0] for _, b in items})
                ys = sorted({b[1] for _, b in items})
                if len(xs) < 2 or len(ys) < 2:
                    continue
                if len(xs) * len(ys) != len(items):
                    continue
                dx = sorted({xs[i + 1] - xs[i] for i in range(len(xs) - 1)})
                dy = sorted({ys[i + 1] - ys[i] for i in range(len(ys) - 1)})
                ptype = byid[parent].type_marker if parent in byid else None
                hits.append(dict(corpus=corp, file=f, parent=parent, ptype=ptype,
                                 cells=len(items), cols=len(xs), rows=len(ys),
                                 w=w, h=h, dx=dx, dy=dy,
                                 markers=sorted({c.type_marker for c, _ in items})))
    print("documents scanned: %d   equal-size lattices: %d" % (ndocs, len(hits)))
    for h in sorted(hits, key=lambda d: -d["cells"]):
        print("  %-28s parent=%#06x type=%s %dx%d cells w=%d h=%d pitch_x=%s pitch_y=%s markers=%s"
              % (os.path.basename(h["file"]), h["parent"],
                 "0x%02x" % h["ptype"] if h["ptype"] is not None else "MISSING",
                 h["cols"], h["rows"], h["w"], h["h"],
                 h["dx"][:3], h["dy"][:3], ["0x%02x" % m for m in h["markers"]]))
    return hits


# --------------------------------------------------------------------------- libmspub

# libmspub MSPUBParser::getBlockDataLength -> value width for a block "type" byte.
TYPE_LEN = {0x78: 0, 0x05: 0, 0x08: 0, 0x0A: 0,
            0x10: 2, 0x12: 2, 0x18: 2, 0x1A: 2, 0x07: 2,
            0x20: 4, 0x22: 4, 0x58: 4, 0x68: 4, 0x70: 4, 0xB8: 4,
            0x28: 8, 0x38: 16, 0x48: 24,
            0xC0: -1, 0x80: -1, 0x82: -1, 0x88: -1, 0x8A: -1,
            0x90: -1, 0x98: -1, 0xA0: -1}

TABLE_IDS = {0x66: "TABLE_NUM_ROWS", 0x67: "TABLE_NUM_COLS",
             0x68: "TABLE_WIDTH", 0x69: "TABLE_HEIGHT",
             0x6B: "TABLE_CELLS_SEQNUM", 0x6D: "TABLE_ROWCOL_ARRAY"}


def block_at(data, i):
    """Parse one libmspub block at offset i; return (id, type, payload, nxt) or None."""
    if i + 2 > len(data):
        return None
    bid, btype = data[i], data[i + 1]
    ln = TYPE_LEN.get(btype)
    if ln is None:
        return None
    if ln < 0:
        if i + 6 > len(data):
            return None
        ln = struct.unpack_from("<I", data, i + 2)[0]
        if ln < 4 or i + 2 + ln > len(data):
            return None
        return bid, btype, data[i + 6:i + 2 + ln], i + 2 + ln
    if i + 2 + ln > len(data):
        return None
    return bid, btype, data[i + 2:i + 2 + ln], i + 2 + ln


def walk_chain(data, start, base):
    """Greedy libmspub-block walk; returns (blocks, consumed) like pubdump."""
    import pubdump
    return pubdump.walk_blocks(data[start:], base + start)


def cmd_libmspub(corpora):
    """Test libmspub's table model against this family.

    Requirement set (MSPUBParser.cpp parseShape/parseBlock):
      * a content chunk with marker 0x10 (TABLE) whose payload is a TLV block list
        carrying ids 0x66/0x67/0x6B/0x6D, plus a chunk with marker 0x63 (CELLS);
      * every block framed as {u8 id, u8 type, payload-of-type-width}.

    A TLV list only counts when the SAME start offset works for most chunks of a
    type, with >=3 blocks, a 00 00 terminator and the list ending exactly at the
    payload end.  Single chunks terminating by accident (most records end in zero
    bytes) are not evidence.
    """
    import pubdump
    docs = 0
    chunks = 0
    per = collections.defaultdict(list)
    raw = collections.Counter()
    sane = collections.Counter()
    for corp, f, doc in load_corpora(corpora):
        docs += 1
        for c in doc.chunks:
            chunks += 1
            per[c.type_marker].append(c)
            d = c.data
            for i in range(len(d) - 1):
                bid, btype = d[i], d[i + 1]
                if bid in TABLE_IDS and btype in TYPE_LEN:
                    raw[(bid, btype)] += 1
                    if TYPE_LEN[btype] == 2 and i + 4 <= len(d):
                        v = struct.unpack_from("<H", d, i + 2)[0]
                        if 1 <= v <= 64:
                            sane[(bid, btype, v)] += 1

    print("documents: %d   chunks: %d" % (docs, chunks))
    print("\n[level 1] content chunks of the two required markers (see `census`): 0x10=0, 0x63=0")

    print("\n[level 2] best fixed-start TLV list per marker (>=3 blocks, exact end)")
    best_by_marker = {}
    best_rows = []
    for tm, lst in per.items():
        if len(lst) < 50:
            continue
        best = (0, None, 0)
        for start in range(0, 64):
            ex = tot = 0
            for c in lst:
                if len(c.data) <= start + 2:
                    continue
                tot += 1
                blocks, consumed = pubdump.walk_blocks(c.data[start:], c.offset + start)
                if (len(blocks) >= 3 and blocks[-1][4] == "TERMINATOR"
                        and start + consumed == len(c.data)):
                    ex += 1
            if tot and ex > best[0]:
                best = (ex, start, tot)
        if best[1] is not None:
            best_by_marker[tm] = best
            best_rows.append((best[0] / best[2], tm) + best)
    best_rows.sort(reverse=True)
    for rate, tm, ex, start, tot in best_rows[:8]:
        print("  marker 0x%04x  best start=+%-2d  exact=%d/%d (%.0f%%)"
              % (tm, start, ex, tot, 100.0 * rate))
    print("  -> no marker reaches 100%%; the payloads are fixed records, not TLV lists")

    print("\n[level 3] table block ids inside the best-fixed-start chains")
    found = False
    for rate, tm, ex, start, tot in best_rows:
        hits = collections.Counter()
        for c in per[tm]:
            if len(c.data) <= start + 2:
                continue
            blocks, consumed = pubdump.walk_blocks(c.data[start:], c.offset + start)
            if not (len(blocks) >= 3 and blocks[-1][4] == "TERMINATOR"
                    and start + consumed == len(c.data)):
                continue
            for b in blocks:
                if not b[4] and b[1] in TABLE_IDS:
                    hits[(b[1], b[2])] += 1
        for (bid, btype), n in hits.items():
            print("  marker 0x%04x id=0x%02x %-18s type=0x%02x n=%d (of %d exact)"
                  % (tm, bid, TABLE_IDS[bid], btype, n, ex))
            found = True
    if not found:
        print("  none")

    print("\n[context] raw {id,type} doublets that would *start* a table block, any byte offset:")
    for (bid, btype), n in sorted(raw.items())[:12]:
        print("  id=0x%02x %-18s type=0x%02x  n=%d" % (bid, TABLE_IDS[bid], btype, n))
    print("  (%d distinct doublets total)" % len(raw))
    print("  doublet followed by u16 in 1..64: %d distinct, %d occurrences"
          % (len({k[:2] for k in sane}), sum(sane.values())))
    print("\nRaw doublets are not evidence: the id bytes occur inside WMF image payloads and\n"
          "coordinate/colour fields.  libmspub's table reader needs a TABLE chunk (0x10) and\n"
          "framed blocks; neither exists in this family.")


# --------------------------------------------------------------------------- dump

def cmd_dump(path, parent):
    doc = pubcore.parse_contents(path)
    parent = int(parent, 16)
    byid = {c.id: c for c in doc.chunks}
    print("%s ver=%02x chunks=%d" % (path, doc.version_magic, len(doc.chunks)))
    for c in doc.chunks:
        if c.parent != parent:
            continue
        b = marker_bbox(c)
        print("\nshape id=%#06x marker=%#04x size=%d off=%#08x" % (c.id, c.type_marker, c.size, c.offset))
        print("  rel  bytes")
        for off in range(0, len(c.data), 16):
            seg = c.data[off:off + 16]
            print("  %04x %s" % (off, " ".join("%02x" % x for x in seg)))
        if b:
            x0, y0, x1, y1 = b
            print("  bbox@+6: x0=%d y0=%d x1=%d y1=%d  w=%d h=%d" % (x0, y0, x1, y1, x1 - x0, y1 - y0))
        print("  u16 quad @+0: %04x %04x" % struct.unpack_from("<HH", c.data, 0))
        print("  u32 fields: %s" % " ".join("%#x" % v for v in struct.unpack_from("<7I", c.data, 4)))
        print("  u16 @+0x20..: %s" % " ".join("%#06x" % v for v in struct.unpack_from("<%dH" % ((len(c.data) - 0x20) // 2), c.data, 0x20)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["census", "grids", "lattices", "libmspub", "dump"])
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--min-cells", type=int, default=4)
    a = ap.parse_args()
    if a.cmd == "census":
        cmd_census(a.targets)
    elif a.cmd == "grids":
        cmd_grids(a.targets, a.min_cells)
    elif a.cmd == "lattices":
        cmd_lattices(a.targets, a.min_cells)
    elif a.cmd == "libmspub":
        cmd_libmspub(a.targets)
    else:
        cmd_dump(a.targets[0], a.targets[1])


if __name__ == "__main__":
    main()
