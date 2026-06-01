import base64, sys, os
# Read base64 from stdin args, decode, write to file
b64_str = sys.argv[1]
out_path = sys.argv[2]
data = base64.b64decode(b64_str)
with open(out_path, "wb") as f:
    f.write(data)
print(f"Wrote {len(data)} bytes to {out_path}")
