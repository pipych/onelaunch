import re

path = r"C:\Users\pshen\.openclaw\workspace\onelaunch\launcher.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = '''def download_file(url: str, dest: Path, callback=None):
    """Download with User-Agent header."""
    from urllib.request import Request, urlopen
    req = Request(url, headers={"User-Agent": "OneLaunch/1.0"})
    with urlopen(req) as resp:
        with open(dest, "wb") as f:
            shutil.copyfileobj(resp, f)'''

new = '''def download_file(raw_url: str, dest: Path, callback=None):
    """Download with User-Agent header and URL encoding."""
    from urllib.request import Request, urlopen
    from urllib.parse import quote
    url = quote(raw_url, safe=':/?#[]@!$&\\'()*+,;=')
    req = Request(url, headers={"User-Agent": "OneLaunch/1.0"})
    with urlopen(req) as resp:
        with open(dest, "wb") as f:
            shutil.copyfileobj(resp, f)'''

content = content.replace(old, new)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("FIXED")
print("verify:", "urllib.parse" in content and "quote(raw_url" in content)
