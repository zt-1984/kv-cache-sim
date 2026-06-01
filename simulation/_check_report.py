import os
from pypdf import PdfReader
pdf = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports", "KV_Cache_Offloading_Report.pdf")
if os.path.exists(pdf):
    r = PdfReader(pdf)
    sz = os.path.getsize(pdf)
    print(f"PDF: {pdf}")
    print(f"Size: {sz/1024:.0f} KB")
    print(f"Pages: {len(r.pages)}")
    for i,p in enumerate(r.pages):
        t = p.extract_text()
        print(f"  P{i+1}: {len(t)} chars, starts: {t[:40]}")
else:
    print(f"PDF NOT FOUND at {pdf}")
