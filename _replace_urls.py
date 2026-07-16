import os

d = r'C:\Users\pshen\.openclaw\workspace\onelaunch'
files = ['launcher.py','updater.py','update_check.py','upload_r2.py','onelaunch-update.json','update-manifest.json','build_all.py','build.ps1']

oldu = 'pub-f6e5d69d8dfd4ec194b0ebc7b4c3de96.r2.dev'
newu = 'update.onelaunch.pp.ua'
oldm = 'pub-61c15faa68244ff5afc5cf17a0054122.r2.dev'
newm = 'modpack.onelaunch.pp.ua'

for fn in files:
    fp = os.path.join(d, fn)
    if not os.path.exists(fp):
        print(f'SKIP {fn} (not found)')
        continue
    with open(fp, 'r', encoding='utf-8') as f:
        c = f.read()
    orig = c
    c = c.replace(oldu, newu)
    c = c.replace(oldm, newm)
    if c != orig:
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(c)
        print(f'OK {fn}')
    else:
        print(f'NOCHANGE {fn}')
print('DONE')
