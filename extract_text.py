import re

with open(r"C:\Users\pshen\.openclaw\workspace\onelaunch\launcher.py", "r", encoding="utf-8") as f:
    content = f.read()

# Write the entire file to a text file for reading
with open(r"C:\Users\pshen\.openclaw\workspace\onelaunch\launcher_text.txt", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Written {len(content)} chars")
