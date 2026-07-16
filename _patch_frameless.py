import re

path = r"C:\Users\pshen\.openclaw\workspace\onelaunch\launcher.py"
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Change 1: frameless window
old = '''    window = webview.create_window(
        "OneLaunch", html=html_with_nick, js_api=api,
        width=1280, height=720, resizable=False
    )'''
new = '''    window = webview.create_window(
        "OneLaunch", html=html_with_nick, js_api=api,
        width=1280, height=720, resizable=False, frameless=True, easy_drag=False
    )'''
assert old in content, "Change 1: old text not found!"
content = content.replace(old, new)

# Change 2: add API methods before def get_nickname
old2 = '''    def get_nickname(self):'''
new2 = '''    def minimize_window(self):
        import webview as _wv
        w = _wv.active_window()
        if w: w.minimize()

    def close_window(self):
        import webview as _wv
        w = _wv.active_window()
        if w: w.destroy()

    def get_nickname(self):'''
assert old2 in content, "Change 2: old text not found!"
content = content.replace(old2, new2)

# Change 3: add titlebar HTML after <body>
old3 = '<body>'
new3 = '''<body>
<div class="titlebar">
  <span class="titlebar-title">OneLaunch</span>
  <div class="titlebar-btns">
    <button class="tb-btn" onclick="pywebview.api.minimize_window()" title="Свернуть">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="5" y1="12" x2="19" y2="12"/></svg>
    </button>
    <button class="tb-btn tb-close" onclick="pywebview.api.close_window()" title="Закрыть">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
    </button>
  </div>
</div>'''
assert old3 in content, "Change 3: <body> not found!"
content = content.replace(old3, new3)

# Change 4: add titlebar CSS before body{ in CSS
old4 = '}\nbody{'
new4 = '''}
/* --- Title bar --- */
.titlebar{
  height:36px;background:#0d1114;
  display:flex;align-items:center;justify-content:space-between;
  padding:0 12px;
  -webkit-app-region:drag;app-region:drag;
  flex-shrink:0;
}
.titlebar-title{
  font-family:'Montserrat','Segoe UI',sans-serif;
  font-size:11px;font-weight:700;color:#6b7280;
  letter-spacing:1px;text-transform:uppercase;
}
.titlebar-btns{display:flex;gap:2px;-webkit-app-region:no-drag;app-region:no-drag}
.tb-btn{
  background:none;border:none;cursor:pointer;
  width:28px;height:28px;display:flex;align-items:center;justify-content:center;
  border-radius:6px;color:#6b7280;transition:all .15s
}
.tb-btn:hover{background:#1f2937;color:#d4d4d4}
.tb-btn.tb-close:hover{background:#ef4444;color:#fff}
.tb-btn svg{width:14px;height:14px}
body{'''
assert old4 in content, "Change 4: CSS body{ not found!"
content = content.replace(old4, new4)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("All 4 changes applied successfully!")

# Verify syntax
import py_compile
py_compile.compile(path, doraise=True)
print("Syntax OK")
