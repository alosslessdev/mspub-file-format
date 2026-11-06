"""Enumerate OLE 'Object N' substorages in Publisher 95/97/98 corpora."""
import sys, glob, json, os, collections
import olefile

CORPORA = ["p95/x", "p97/x", "p97deluxe/x", "p98/x"]


def path_str(p):
    return '/'.join(x.decode('latin-1') if isinstance(x, bytes) else x for x in p)


def scan(files):
    recs = []
    for f in files:
        try:
            o = olefile.OleFileIO(f)
        except Exception as e:
            print("OPENFAIL", f, e, file=sys.stderr)
            continue
        for p in o.listdir():
            parts = [x.decode('latin-1') if isinstance(x, bytes) else x for x in p]
            # object storages: any component named "Object N" or "Objects"
            for i, comp in enumerate(parts[:-1]):
                if comp == "Objects" and i + 1 < len(parts) - 1:
                    obj = parts[i + 1]
                    stream = parts[i + 2]
                    recs.append({
                        "file": f,
                        "storage": '/'.join(parts[:i + 2]),
                        "objects_index": i,
                        "obj": obj,
                        "stream": stream,
                        "size": o.get_size(p),
                    })
                    break
        o.close()
    return recs


def main():
    all_files = []
    for c in CORPORA:
        all_files += sorted(glob.glob(c + '/**/*.PUB', recursive=True))
    recs = scan(all_files)
    json.dump(recs, open(sys.argv[1] if len(sys.argv) > 1 else 'tools/p97_objects.json', 'w'), indent=0)
    print("files scanned", len(all_files), "records", len(recs))
    files_with = len({r['file'] for r in recs})
    print("files with objects", files_with)
    combo = collections.Counter()
    per_file = collections.defaultdict(set)
    for r in recs:
        per_file[r['file']].add(r['stream'])
    for f, s in per_file.items():
        combo[tuple(sorted(s))] += 1
    for k, v in combo.most_common():
        print(v, k)
    print("--- n objects per file ---")
    no = collections.Counter()
    objs = collections.defaultdict(set)
    for r in recs:
        objs[r['file']].add(r['storage'])
    for f, s in objs.items():
        no[len(s)] += 1
    print(sorted(no.items()))


if __name__ == "__main__":
    main()
