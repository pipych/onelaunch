import sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines[int(sys.argv[2]):int(sys.argv[3])], start=1):
    print(f"{i}:{line.rstrip()}")
