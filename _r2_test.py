import os, sys, boto3, io, struct, zlib

# Load .env
env = {}
with open('C:/Users/pshen/.openclaw/workspace/onelaunch/.env') as f:
    for line in f:
        if '=' in line:
            k, v = line.strip().split('=', 1)
            env[k] = v

print('ACCOUNT:', env['R2_ACCOUNT_ID'][:8])
print('BUCKET:', env['R2_BUCKET'])

s3 = boto3.client('s3',
    endpoint_url=f"https://{env['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
    aws_access_key_id=env['R2_ACCESS_KEY_ID'],
    aws_secret_access_key=env['R2_SECRET_ACCESS_KEY'],
    region_name='auto')

# Create small PNG
def make_png(w, h):
    raw = b''
    for y in range(h):
        raw += b'\x00' + b'\x00\x00\x00\x00' * w
    def chunk(typ, data):
        c = typ + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')

try:
    # Test upload to olskins
    s3.upload_fileobj(io.BytesIO(make_png(64, 64)), 'olskins', 'skins/_test_.png',
                      ExtraArgs={'ContentType': 'image/png'})
    print('Upload to olskins: OK')
except Exception as e:
    print(f'Upload FAILED: {type(e).__name__}: {e}')

try:
    # Test upload to olupdate
    s3.upload_fileobj(io.BytesIO(make_png(64, 64)), 'olupdate', '_test_.png',
                      ExtraArgs={'ContentType': 'image/png'})
    print('Upload to olupdate: OK')
except Exception as e:
    print(f'Upload FAILED: {type(e).__name__}: {e}')
