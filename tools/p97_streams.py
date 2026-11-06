"""Root-level entry census per corpus (streams + storages), full paths."""
import sys, os, glob, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import olefile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPORA = [("p95", "p95/x"), ("p97", "p97/x"), ("p97deluxe", "p97deluxe/x"), ("p98", "p98/x")]

for ver, rel in CORPORA:
    files = sorted(glob.glob(os.path.join(ROOT, rel, "**", "*.PUB"), recursive=True))
    root = collections.Counter()
    nested = collections.Counter()
    n = 0
    for f in files:
        n += 1
        try:
            o = olefile.OleFileIO(f)
        except Exception as e:
            print("ERR", f, e)
            continue
        for path in o.listdir(streams=True, storages=True):
            p = "/".join(path)
            if len(path) == 1:
                root[p] += 1
            else:
                nested[p] += 1
        o.close()
    print("== %s  (%d files) ==" % (ver, n))
    print("  root entries:", ", ".join("%s=%d" % (k, v) for k, v in sorted(root.items())))
    print("  nested paths:", ", ".join("%s=%d" % (k, v) for k, v in sorted(nested.items())))
    print()
