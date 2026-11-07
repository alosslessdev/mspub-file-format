import sys, struct, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

path = sys.argv[1]
q = pubcore.read_stream(path, 'Quill/QuillSub/CONTENTS')


def dirdump(q):
    recs = []
    off = 0x18
    while True:
        cap, cnt, nxt = struct.unpack_from('<HHI', q, off)
        for i in range(cnt):
            r = q[off + 8 + 24 * i: off + 8 + 24 * (i + 1)]
            sz, name, id_, f1, f2, name2, o, l = struct.unpack('<H4sHHH4sII', r)
            recs.append((name, id_, o, l))
        if nxt == 0xFFFFFFFF:
            break
        off = nxt
    return recs


recs = dirdump(q)
print([(r[0], r[1], hex(r[2]), r[3]) for r in recs])
m = [r for r in recs if r[0] == b'MCLD'][0]
o, ln = m[2], m[3]
tag, cnt = struct.unpack_from('<II', q, o)
ids = struct.unpack_from('<%dI' % cnt, q, o + 8)
p = o + 8 + 4 * cnt


def readstream(p):
    sz = struct.unpack_from('<I', q, p)[0]
    return q[p:p + sz], p + sz


def fields(b):
    out = {}
    i = 4
    while i + 2 <= len(b):
        t = struct.unpack_from('<H', b, i)[0]
        fid = t & 0x7ff
        code = t >> 11
        if code == 0:
            out[fid] = ('f', False); i += 2
        elif code == 1:
            out[fid] = ('f', True); i += 2
        elif code == 2:
            out[fid] = ('B', b[i + 2]); i += 4
        elif code == 3:
            out[fid] = ('W', struct.unpack_from('<H', b, i + 2)[0]); i += 4
        elif code == 4:
            out[fid] = ('D', struct.unpack_from('<I', b, i + 2)[0]); i += 6
        elif code == 5:
            out[fid] = ('Q', struct.unpack_from('<II', b, i + 2)); i += 10
        else:
            out[-1] = ('bad', code, fid); break
    return out


for k in range(cnt):
    a, p = readstream(p)
    bs, p = readstream(p)
    n = struct.unpack_from('<I', q, p)[0]
    p += 4
    blocks = []
    for j in range(n):
        b, p = readstream(p)
        blocks.append(fields(b))
    fa = fields(a)
    d = {kk: v[1] for kk, v in blocks[0].items() if v[0] == 'D'}
    w = {kk: v[1] for kk, v in blocks[0].items() if v[0] == 'W'}
    print('id', ids[k], 'A', fa, 'D', d, 'W', w)
print('end', p, len(q), 'nobj', cnt)
