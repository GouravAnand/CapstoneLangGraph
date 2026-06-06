import pdfplumber, io

with open('notice_2.pdf', 'rb') as f:
    data = f.read()

with pdfplumber.open(io.BytesIO(data)) as pdf:
    text = '\n'.join(p.extract_text() or '' for p in pdf.pages)

print("Length:", len(text.strip()))
print("Text preview:", repr(text[:300]))