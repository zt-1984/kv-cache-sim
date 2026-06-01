import sys, os
# Read the report content from a separate file
main_path = os.path.join(os.path.dirname(__file__), "_rep_main.py")
print(f"Reading: {main_path}")
if os.path.exists(main_path):
    content = open(main_path, "r", encoding="utf-8").read()
    with open(os.path.join(os.path.dirname(__file__), "generate_report.py"), "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Written {len(content)} bytes")
else:
    print(f"NOT FOUND: {main_path}")
