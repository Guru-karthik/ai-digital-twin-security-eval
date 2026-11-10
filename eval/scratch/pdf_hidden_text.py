"""Phase 0 experiment: what does pypdf return for hidden/tiny text? Fake data only."""
import io
import sys
from pypdf import PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.colors import white, black

buf = io.BytesIO()
c = canvas.Canvas(buf)
c.setTitle("META-CANARY-TITLE")
c.setAuthor("META-CANARY-AUTHOR")
c.setFillColor(black); c.setFont("Helvetica", 12)
c.drawString(72, 750, "PLAIN-CANARY visible text")
c.setFillColor(white); c.drawString(72, 700, "WHITE-CANARY white on white")
c.setFillColor(black); c.setFont("Helvetica", 1); c.drawString(72, 650, "TINY-CANARY one point font")
c.setFont("Helvetica", 12); c.drawString(-500, 600, "OFFPAGE-CANARY outside page box")
c.save()
buf.seek(0)
r = PdfReader(buf)
text = "".join(p.extract_text() or "" for p in r.pages)
for name in ["PLAIN", "WHITE", "TINY", "OFFPAGE"]:
    print(f"{name}-CANARY in extracted text:", f"{name}-CANARY" in text)
meta = r.metadata or {}
print("metadata keys:", sorted(meta.keys()))
print("metadata canary in extract_text (context.py path ignores metadata):", "META-CANARY" in text)
print("pypdf", __import__("pypdf").__version__, "python", sys.version.split()[0])
