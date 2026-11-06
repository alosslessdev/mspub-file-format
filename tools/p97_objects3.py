"""Final aggregate stats for the objects slice."""
import glob, collections, struct, statistics
import olefile

CORP = ["p95/x", "p97/x", "p97deluxe/x", "p98/x"]
STREAMS = ['\x01CompObj', '\x01Ole', '\x02OlePres000', '\x02OlePres001',
           '\x01Ole10Native', '\x01Ole10ItemName', '\x03Internal', 'Contents']


def comp_obj_class(d):
    off = 28
    out = []
    for _ in range(3):
        if off + 4 > len(d):
            return out
        n = struct.unpack_from('<I', d, off)[0]
        off += 4
        out.append(d[off:off + n].rstrip(b'\0').decode('latin-1', 'replace'))
        off += n
    return out


def main():
    print("corpus | files | files_with_Objects | objects")
    grand = collections.Counter()
    allst = collections.defaultdict(list)
    combos = collections.Counter()
    nums = collections.Counter()
    for c in CORP:
        files = sorted(glob.glob(c + '/**/*.PUB', recursive=True))
        nf = len(files)
        wf = 0
        nobj = 0
        for fn in files:
            try:
                o = olefile.OleFileIO(fn)
            except Exception:
                continue
            objs = collections.defaultdict(set)
            for p in o.listdir():
                parts = [x.decode('latin-1') if isinstance(x, bytes) else x for x in p]
                if len(parts) >= 3 and parts[0] == 'Objects':
                    objs[parts[1]].add(parts[2])
                    allst[parts[2]].append(o.get_size(p))
                    if parts[2] == '\x01CompObj':
                        cls = comp_obj_class(o.openstream(p).read())
                        combos[(c, cls[-1] if cls else '', tuple(sorted(objs[parts[1]])))] += 0
            if objs:
                wf += 1
            for name, ss in objs.items():
                nobj += 1
                try:
                    nums[int(name.split()[1])] += 1
                except Exception:
                    pass
                combos[(tuple(sorted(ss)))] += 1
            o.close()
        grand[c] = (nf, wf, nobj)
        print(f"{c} | {nf} | {wf} | {nobj}")
    print()
    print("stream | instances | min | median | max")
    for s in STREAMS:
        v = allst[s]
        if v:
            print(f"{s} | {len(v)} | {min(v)} | {int(statistics.median(v))} | {max(v)}")
    print()
    print("object stream sets:")
    for k, v in combos.most_common():
        if isinstance(k, tuple) and k and isinstance(k[0], tuple):
            print(v, k[0])
    print()
    print("object numbers: min", min(nums), "max", max(nums))


if __name__ == '__main__':
    main()
