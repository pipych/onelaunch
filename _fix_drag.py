"""Fix window dragging for OneLaunch frameless window."""
import re

path = r"C:\Users\pshen\.openclaw\workspace\onelaunch\launcher.py"
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Check what we have
has_move_win = 'def move_win(' in content
has_move_api = 'move_win' in content
has_drag_js = 'dragging = false' in content.lower() or 'dragging = False' in content
has_frameless = 'frameless=True' in content

print(f"move_win in API: {has_move_win}")
print(f"move_win anywhere: {has_move_api}")
print(f"JS drag code: {has_drag_js}")
print(f"frameless=True: {has_frameless}")

# If move_win is missing, add it before close_window
if not has_move_win:
    old = '    def close_window(self):'
    new = '''    def move_win(self, dx: int, dy: int):
        import webview as _wv
        w = _wv.active_window()
        if w:
            try:
                w.move(w.x + dx, w.y + dy)
            except Exception:
                pass

    def close_window(self):'''
    if old in content:
        content = content.replace(old, new)
        print("Added move_win to API")
    else:
        print("ERROR: close_window not found in API!")

# Check if drag JS exists - if not, add it before </script>
if 'dragging = false' not in content.lower() and 'var dragging' not in content.lower():
    drag_js = '''
// Window drag (frameless)
(function(){
  var dragging = false, sx = 0, sy = 0;
  document.addEventListener('mousedown', function(e){
    if (e.target.closest('.tb-btn') || e.target.closest('.bottom-bar') || e.target.closest('button') || e.target.tagName === 'INPUT') return;
    dragging = true; sx = e.screenX; sy = e.screenY;
    document.body.style.cursor = 'grabbing';
  });
  document.addEventListener('mousemove', function(e){
    if (!dragging) return;
    pywebview.api.move_win(e.screenX - sx, e.screenY - sy);
    sx = e.screenX; sy = e.screenY;
  });
  document.addEventListener('mouseup', function(){
    dragging = false;
    document.body.style.cursor = '';
  });
})();
'''
    old_script = '</script>'
    if old_script in content:
        content = content.replace(old_script, drag_js + '\n</script>')
        print("Added JS drag handler")
    else:
        print("ERROR: </script> not found!")
else:
    print("JS drag code already present")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify syntax
import py_compile
py_compile.compile(path, doraise=True)
print("Syntax OK")
print("Done - file updated")
