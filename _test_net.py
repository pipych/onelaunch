"""Quick connectivity test for the frozen exe."""
import sys
import time

print("Python:", sys.executable)
print("Frozen:", getattr(sys, "frozen", False))
print()

# Test 1: DNS resolution
import socket
try:
    ip = socket.gethostbyname("update.onelaunch.pp.ua")
    print(f"DNS OK: update.onelaunch.pp.ua -> {ip}")
except Exception as e:
    print(f"DNS FAIL: {e}")

# Test 2: TCP connect
try:
    s = socket.create_connection(("update.onelaunch.pp.ua", 443), timeout=10)
    s.close()
    print("TCP OK: port 443 reachable")
except Exception as e:
    print(f"TCP FAIL: {e}")

# Test 3: HTTPS via requests
try:
    import requests
    r = requests.get("https://update.onelaunch.pp.ua/metadata/timestamp.json", timeout=10)
    print(f"HTTPS OK: status={r.status_code}")
except Exception as e:
    print(f"HTTPS FAIL: {e}")

# Test 4: certifi bundle
try:
    import certifi
    cb = certifi.where()
    import os
    print(f"certifi OK: {cb} (exists={os.path.exists(cb)})")
except Exception as e:
    print(f"certifi FAIL: {e}")

# Test 5: tufup check_for_updates
try:
    print()
    print("--- tufup check ---")
    import _update_tuf
    _update_tuf.init_for_updater("0.3.3")
    result = _update_tuf.check_and_update("0.3.3")
    print(f"check_and_update result: {result}")
except Exception as e:
    import traceback
    print(f"tufup FAIL: {e}")
    traceback.print_exc()

print()
print("All tests done.")
time.sleep(2)
