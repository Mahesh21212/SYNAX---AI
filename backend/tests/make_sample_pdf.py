"""Generate a small real PDF for end-to-end verification."""

import sys
from pathlib import Path

target = Path(sys.argv[1])
target.parent.mkdir(parents=True, exist_ok=True)

lines = [
    "SYNAX AI verification document.",
    "Quarterly revenue was 4.2 million.",
    "Operating margin fell 180 basis points.",
]

content = "BT /F1 12 Tf 72 720 Td 14 TL " + " ".join(
    f"({line}) Tj T*" for line in lines
) + " ET"

objs = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
    "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
    f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
]

out = "%PDF-1.4\n"
offsets = []
for index, obj in enumerate(objs, start=1):
    offsets.append(len(out))
    out += f"{index} 0 obj\n{obj}\nendobj\n"

xref = len(out)
out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n"
for offset in offsets:
    out += f"{offset:010d} 00000 n \n"
out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"

target.write_bytes(out.encode("latin-1"))
print(f"wrote {target} ({target.stat().st_size} bytes)")
