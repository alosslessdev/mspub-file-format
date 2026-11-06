"""Regenerate tools/palette.py from the palette table in spec/09-chunk-palette.md."""
import re
import sys

text = open("spec/09-chunk-palette.md", encoding="utf-8").read()
rows = re.findall(r"^\|\s*0x([0-9A-Fa-f]{2})\s*\|\s*`?0x([0-9A-Fa-f]{6})`?\s*\|\s*(\d+),(\d+),(\d+)",
                  text, re.M)
tbl = {int(i, 16): (int(r), int(g), int(b)) for i, _h, r, g, b in rows}
lines = ['"""Default Publisher 95-98 palette: index -> RGB.', '',
         'Generated from spec/09-chunk-palette.md (9.2) so the table cannot drift from the',
         'specification. Regenerate with tools/gen_palette.py.', '"""', '', 'PALETTE = {']
for i in sorted(tbl):
    lines.append("    0x%02X: (%3d, %3d, %3d)," % (i, *tbl[i]))
lines += ['}', '', '', 'def resolve_palette(index: int):', '    return PALETTE.get(index & 0xFF)', '']
open("tools/palette.py", "w", encoding="utf-8").write("\n".join(lines))
print("wrote %d entries" % len(tbl))
