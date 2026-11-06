"""Map CFB stream offsets to absolute file offsets (for evidence citations)."""
import sys
import olefile


def chain(o, first):
    out = []
    s = first
    seen = set()
    while s < 0xFFFFFFFA and s not in seen:
        seen.add(s)
        out.append(s)
        s = o.fat[s]
    return out


def tree_children(o, sid):
    """Yield direntry ids in the red-black tree rooted at sid."""
    stack = [sid]
    seen = set()
    while stack:
        i = stack.pop()
        if i in (0xFFFFFFFF, 0xFFFFFFFE) or i in seen:
            continue
        seen.add(i)
        e = o.direntries[i]
        if e is None:
            continue
        stack.append(e.sid_left)
        stack.append(e.sid_right)
        yield i


def build_paths(o):
    paths = {}

    def walk(sid, prefix):
        for i in tree_children(o, sid):
            e = o.direntries[i]
            nm = e.name if isinstance(e.name, str) else e.name.decode('latin-1')
            p = prefix + '/' + nm if prefix else nm
            paths[p] = i
            if e.entry_type == 1:
                walk(e.sid_child, p)
    walk(o.root.sid_child, '')
    return paths


def abs_offset(o, path, off):
    e = o.direntries[build_paths(o)[path]]
    if e.size >= o.mini_stream_cutoff_size:
        ch = chain(o, e.isectStart)
        sec = off // o.sector_size
        return 512 + ch[sec] * o.sector_size + (off % o.sector_size)
    rch = chain(o, o.root.isectStart)
    sec = off // o.mini_sector_size
    return 512 + rch[sec] * o.sector_size + (off % o.mini_sector_size)


if __name__ == '__main__':
    o = olefile.OleFileIO(sys.argv[1])
    for p in sorted(build_paths(o)):
        print(p)
    o.close()
