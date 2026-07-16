#!/usr/bin/env python
"""Apply all UI fixes to OneLaunch launcher.py"""
import re

with open(r"C:\Users\pshen\.openclaw\workspace\onelaunch\launcher.py", "r", encoding="utf-8") as f:
    content = f.read()

# Extract HTML section
m = re.search(r"HTML = r'''([\s\S]*?)'''", content)
if not m:
    print("ERROR: HTML section not found")
    exit(1)

html = m.group(1)

# ============================================================
# FIX 1: Move nickname to bottom-left, narrower, pre-fill from config
# ============================================================
# Find the .main-nick CSS and update it
html = re.sub(
    r'\.main-nick\{[^}]*\}',
    '.main-nick{position:fixed;bottom:32px;left:32px;z-index:2;background:rgba(9,11,14,.8);color:#d4d4d4;border:1px solid #1f2937;border-radius:14px;padding:10px 16px;width:190px;font-size:13px;font-weight:700;text-align:center;outline:none;transition:border-color .3s,box-shadow .3s}',
    html
)

html = re.sub(
    r'\.main-nick:focus\{[^}]*\}',
    '.main-nick:focus{border-color:#c0ff00;box-shadow:0 0 12px rgba(192,255,0,.15)}',
    html
)

html = re.sub(
    r'\.main-nick::placeholder\{[^}]*\}',
    '.main-nick::placeholder{color:#374151;font-weight:400}',
    html
)

# Add pulsing animation for empty nickname
if '@keyframes pulse' not in html:
    pulse_css = '@keyframes pulse-border{0%,100%{border-color:#1f2937;box-shadow:0 0 0 rgba(192,255,0,0)}50%{border-color:#c0ff00;box-shadow:0 0 16px rgba(192,255,0,.3)}}.main-nick:empty:not(:focus){animation:pulse-border 2s infinite}'
    html = html.replace('</style>', pulse_css + '\n</style>')

# The main-nick empty animation should work when value is empty
html = html.replace('</style>', '.main-nick.empty-nick{animation:pulse-border 2s infinite}\n</style>')

# ============================================================
# FIX 2: Add tooltip styles for icon-only buttons
# ============================================================
tooltip_css = '''
[data-tooltip]{position:relative}
[data-tooltip]:hover::after{content:attr(data-tooltip);position:absolute;bottom:calc(100% + 8px);left:50%;transform:translateX(-50%);background:rgba(20,23,28,.95);color:#d4d4d4;font-size:11px;font-weight:600;padding:6px 14px;border-radius:12px;border:1px solid rgba(192,255,0,.2);white-space:nowrap;pointer-events:none;z-index:999;opacity:1;transition:opacity .2s;box-shadow:0 4px 16px rgba(0,0,0,.5)}
[data-tooltip]:not(:hover)::after{opacity:0}
'''
html = html.replace('</style>', tooltip_css + '</style>')

# ============================================================
# FIX 3: Add folder button with tooltip (if missing)
# ============================================================
# Look for the existing folder-btn or add it
if 'folder-btn' not in html:
    # Add CSS for folder button
    folder_css = '.folder-btn{position:fixed;bottom:32px;right:96px;z-index:2;width:40px;height:40px;background:rgba(9,11,14,.8);border:1px solid #1f2937;border-radius:12px;color:#6b7280;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all .2s}.folder-btn:hover{color:#c0ff00;border-color:#c0ff00;background:rgba(192,255,0,.08)}'
    html = html.replace('</style>', folder_css + '\n</style>')
    
    # Add folder button HTML after the <div id="main"> opening tag
    folder_html = '<button class="folder-btn" data-tooltip="Папка игры" onclick="openFolder()"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg></button>'
    html = html.replace('<div id="main">', '<div id="main">\n  ' + folder_html)

# ============================================================
# FIX 4: Status icon - change to "code" icon (< >) in bottom right
# ============================================================
# Add CSS for status button
status_css = '.status-btn{position:fixed;bottom:32px;right:32px;z-index:2;width:40px;height:40px;background:rgba(9,11,14,.8);border:1px solid #1f2937;border-radius:12px;color:#6b7280;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all .2s;font-family:monospace;font-size:14px;font-weight:700}.status-btn:hover{color:#c0ff00;border-color:#c0ff00;background:rgba(192,255,0,.08)}'
html = html.replace('</style>', status_css + '\n</style>')

# Add status code icon button HTML to main div
# Use a code tag icon: < >
status_html = '<button class="status-btn" data-tooltip="Версия 0.2.5" id="versionBtn"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg></button>'
html = html.replace('<div id="main">', '<div id="main">\n  ' + status_html)

# ============================================================
# FIX 5: Pre-fill nickname from config on load
# ============================================================
# Update the window load handler to handle empty/empty-nick class
old_load = r"""window.addEventListener\("load",function\(\)\{"""
new_load = """window.addEventListener("load",function(){
  window.pywebview.api.get_nickname().then(function(n){
    if(n){
      mNick.value=n;
      mNick.classList.remove('empty-nick');
      launchBtn.disabled=false;
      launchBtn.textContent="ИГРАТЬ";
    }else{
      mNick.classList.add('empty-nick');
    }
  });"""

html = re.sub(old_load, new_load, html)

# Also handle input event to remove empty-nick class
html = re.sub(
    r"""mNick\.addEventListener\("input",function\(\)\{""",
    """mNick.addEventListener("input",function(){
  if(mNick.value.trim()){mNick.classList.remove('empty-nick');}else{mNick.classList.add('empty-nick');}""",
    html
)

# ============================================================
# Write modified content back
# ============================================================
new_content = content.replace(m.group(1), html)

with open(r"C:\Users\pshen\.openclaw\workspace\onelaunch\launcher.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("DONE - launcher.py updated with all 4 fixes")
print("1. Nickname field: bottom-left, narrower, pre-fill from config")
print("2. Folder button: opens .minecraft in Explorer with tooltip")
print("3. Status icon: code icon (</>) with version tooltip")
print("4. Tooltips: on hover for all icon-only buttons")
