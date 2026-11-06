"""Dump CFB (OLE2) container internals of Publisher 95/97/98 documents."""
import sys, glob
import olefile

def dump(f, entries=True):
    o = olefile.OleFileIO(f)
    hdr = (
        f"sig={o.header_signature.hex()} minor={o.minor_version} dll={o.dll_version} "
        f"ssz={o.sector_size} mssz={o.mini_sector_size} cutoff={o.mini_stream_cutoff_size} "
        f"nb_sect={o.nb_sect} nfat={o.num_fat_sectors} nmfat={o.num_mini_fat_sectors} "
        f"ndir={o.num_dir_sectors} firstdir={o.first_dir_sector} firstfat={o.first_difat_sector} "
        f"ndifat={o.num_difat_sectors} clsid={o.header_clsid}"
    )
    print(f.split('/')[-1], hdr)
    if entries:
        for i, e in enumerate(o.direntries):
            if e is None:
                continue
            n = e.name.decode('latin-1') if isinstance(e.name, bytes) else str(e.name)
            print(f"  {i:2d} t={e.entry_type} {n!r:24s} size={e.size:7d} start={e.isectStart:5d} "
                  f"L={e.sid_left:2d} R={e.sid_right:2d} C={e.sid_child:2d} col={e.color}")
    o.close()

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        args = sorted(glob.glob('p95/x/**/*.PUB', recursive=True))[:3]
    for a in args:
        dump(a)
