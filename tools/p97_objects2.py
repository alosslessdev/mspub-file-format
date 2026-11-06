"""Build a per-object record table: streams, class names, pres kinds."""
import sys, glob, json, collections, struct
import olefile

CORP = ["p95/x", "p97/x", "p97deluxe/x", "p98/x"]


def pstr(p):
    return '/'.join(x.decode('latin-1') if isinstance(x, bytes) else x for x in p)


def parse_compobj(d):
    if len(d) < 28:
        return None
    hdr = d[:12]
    blk = d[12:28]
    off = 28
    strs = []
    for _ in range(3):
        if off + 4 > len(d):
            return None
        n = struct.unpack_from('<I', d, off)[0]
        off += 4
        if n > len(d) - off:
            return None
        strs.append(d[off:off + n])
        off += n
    return hdr, blk, strs, d[off:]


def pres_kind(d):
    n = len(d)
    if n < 12:
        return 'short'
    if n >= 40 and struct.unpack_from('<I', d, 0x24)[0] == n - 40 and d[0x28:0x2a] == b'\x01\x00':
        return 'wmf'
    if d[0x28:0x2a] == b'\xd7\xcd':
        return 'wmf-placeable'
    if d[8:12] in (b'\x0c\x00\x15\x00', b'\x0c\x00\x14\x00', b'\x0c\x00\x13\x00'):
        return 'devmode'
    return 'other'


def main():
    rows = []
    for c in CORP:
        for fn in sorted(glob.glob(c + '/**/*.PUB', recursive=True)):
            try:
                o = olefile.OleFileIO(fn)
            except Exception:
                continue
            objs = collections.defaultdict(dict)
            for p in o.listdir():
                parts = [x.decode('latin-1') if isinstance(x, bytes) else x for x in p]
                if len(parts) >= 3 and parts[0] == 'Objects':
                    objs[parts[1]][parts[2]] = o.get_size(p)
            for name, streams in objs.items():
                rec = {'corpus': c, 'file': fn, 'obj': name,
                       'streams': sorted(streams), 'sizes': streams}
                try:
                    co = o.openstream(['Objects', name, '\x01CompObj']).read()
                    r = parse_compobj(co)
                    if r:
                        rec['hdr'] = r[0].hex()
                        rec['blk'] = r[1].hex()
                        rec['strs'] = [s.rstrip(b'\0').decode('latin-1') for s in r[2]]
                        rec['tail'] = r[3][:4].hex()
                        rec['complen'] = len(co)
                except Exception:
                    pass
                for nm in ('\x02OlePres000', '\x02OlePres001'):
                    if nm in streams:
                        d = o.openstream(['Objects', name, nm]).read()
                        rec['kind' + nm[-3:]] = pres_kind(d)
                        if pres_kind(d) == 'wmf':
                            rec['wmfsize' + nm[-3:]] = struct.unpack_from('<I', d, 0x24)[0]
                            rec['ext' + nm[-3:]] = struct.unpack_from('<II', d, 0x1c)
                if '\x01Ole10Native' in streams:
                    d = o.openstream(['Objects', name, '\x01Ole10Native']).read()
                    rec['native'] = d[:8].hex()
                    rec['nativelen'] = len(d)
                rows.append(rec)
            o.close()
    json.dump(rows, open('tools/p97_objects.json', 'w'), indent=0)
    print('objects', len(rows))
    ct = collections.Counter()
    for r in rows:
        cls = tuple(r.get('strs', []))
        ct[(cls, r.get('kind000'), r.get('kind001'))] += 1
    for k, v in ct.most_common(40):
        print(v, k)


if __name__ == '__main__':
    main()
