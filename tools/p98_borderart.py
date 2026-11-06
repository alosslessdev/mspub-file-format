#!/usr/bin/env python3
"""Decode Publisher 95/97/98 border-art .BDR containers.

Layout (confirmed by corpus measurement + decomp98 FUN_0048292a):
  +0x00  char[2]  magic 'XT' (0x5458 LE); 0x6cf8 = wide-char variant
  +0x02  u16      version (1)
  +0x04  u16      entry count N
  +0x06  N * 42   ANSI name, NUL-terminated, zero padded (84 bytes if magic 0x6cf8)
  +..    N * 22   entry records
  +..     22      sentinel record (8 tile offsets all == EOF)
  +..    blobs    concatenated per-entry tile blobs (each tile = standard WMF)

Entry record (22 bytes):
  +0  u16 a0
  +2  u16 a1
  +4  u16 a2
  +6  u16 tileOff[8]   offsets relative to the START OF THIS RECORD
Each tile k spans [rec+tileOff[k], rec+next_higher_offset) where the last one ends
at the blob end (= record of the *sentinel* + sentinel tile offset).

Usage: python tools/p98_borderart.py <file-or-dir> [--extract DIR]
"""
import glob
import os
import struct
import sys

MAGIC_XT = 0x5458
MAGIC_WIDE = 0x6CF8


def parse(path):
    d = open(path, 'rb').read()
    magic = struct.unpack_from('<H', d, 0)[0]
    ver = struct.unpack_from('<H', d, 2)[0]
    n = struct.unpack_from('<H', d, 4)[0]
    recsize = 42 if magic == MAGIC_XT else 84
    doc = {'path': path, 'size': len(d), 'magic': magic, 'version': ver,
           'count': n, 'recsize': recsize, 'entries': [], 'sentinel': None}
    base = 6 + recsize * n
    sent_off = base + 22 * n
    for i in range(n):
        raw = d[6 + i * recsize: 6 + (i + 1) * recsize]
        if recsize == 84:
            name = raw.decode('utf-16-le', 'replace').split('\x00')[0]
        else:
            name = raw.split(b'\x00')[0].decode('latin-1')
        rec_off = base + i * 22
        a0, a1, a2 = struct.unpack_from('<3H', d, rec_off)
        tiles = list(struct.unpack_from('<8H', d, rec_off + 6))
        doc['entries'].append({'index': i, 'name': name, 'raw_name': raw,
                               'rec_off': rec_off, 'a0': a0, 'a1': a1, 'a2': a2,
                               'tile_off': tiles, 'tiles': []})
    sa = struct.unpack_from('<3H', d, sent_off)
    st = list(struct.unpack_from('<8H', d, sent_off + 6))
    doc['sentinel'] = {'off': sent_off, 'a': sa, 'tile_off': st}
    # resolve tile extents against the union of all offsets in the file
    allpts = {}
    for e in doc['entries']:
        for t in e['tile_off']:
            allpts[e['rec_off'] + t] = None
    sent_abs = sent_off + st[0]
    for e in doc['entries']:
        for k, t in enumerate(e['tile_off']):
            p = e['rec_off'] + t
            nxt = min([q for q in allpts if q > p] or [sent_abs])
            e['tiles'].append({'k': k, 'abs': p, 'next': nxt,
                               'span': nxt - p,
                               'sig': d[p:p + 6], 'hdr': d[p:p + 18]})
    return doc


def wmf_size(hdr):
    """declared size in bytes of a standard (non-placeable) WMF header."""
    if len(hdr) < 18 or hdr[0:4] != b'\x01\x00\x09\x00':
        return None
    return struct.unpack_from('<I', hdr, 6)[0] * 2


def validate(doc):
    bad = []
    for e in doc['entries']:
        for t in e['tiles']:
            if t['sig'][:4] != b'\x01\x00\x09\x00':
                bad.append((e['index'], t['k'], 'sig', t['abs']))
                continue
            ws = wmf_size(t['hdr'])
            if ws != t['span']:
                bad.append((e['index'], t['k'], 'span %d != wmf %s' % (t['span'], ws), t['abs']))
    return bad


def extract(doc, outdir):
    os.makedirs(outdir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(doc['path']))[0]
    d = open(doc['path'], 'rb').read()
    written = []
    for e in doc['entries']:
        for t in e['tiles']:
            if t['sig'][:4] != b'\x01\x00\x09\x00':
                continue
            name = '%s_e%02d_t%d.wmf' % (stem, e['index'], t['k'])
            p = os.path.join(outdir, name)
            open(p, 'wb').write(d[t['abs']:t['next']])
            written.append(p)
    return written


def main():
    args = [a for a in sys.argv[1:]]
    outdir = None
    if '--extract' in args:
        i = args.index('--extract')
        outdir = args[i + 1]
        del args[i:i + 2]
    targets = []
    for a in args:
        targets += glob.glob(os.path.join(a, '*.BDR')) if os.path.isdir(a) else [a]
    for p in sorted(targets):
        doc = parse(p)
        bad = validate(doc)
        ntiles = sum(len(e['tiles']) for e in doc['entries'])
        print('%-14s magic=%#06x ver=%d n=%-3d size=%-6d tiles=%-4d bad=%d'
              % (os.path.basename(p), doc['magic'], doc['version'], doc['count'],
                 doc['size'], ntiles, len(bad)))
        for b in bad[:5]:
            print('    BAD entry=%d tile=%d %s abs=%#x' % b)
        if outdir:
            w = extract(doc, outdir)
            print('    extracted %d wmf' % len(w))


if __name__ == '__main__':
    main()
