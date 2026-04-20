import tarfile
import os

src = os.path.expanduser(r'~\.qlib\qlib_data\qlib_bin.tar.gz')
dst = os.path.expanduser(r'~\.qlib\qlib_data\cn_data')
os.makedirs(dst, exist_ok=True)

print(f'Source: {src}')
print(f'Destination: {dst}')
print('Opening archive...')

with tarfile.open(src, 'r:gz') as t:
    members = t.getmembers()
    print(f'Total entries: {len(members)}')
    
    # Detect top-level directory name
    top_dirs = set()
    for m in members:
        parts = m.name.split('/')
        if parts[0]:
            top_dirs.add(parts[0])
    print(f'Top-level dirs in archive: {top_dirs}')
    
    # Strip top-level directory
    extracted = 0
    for m in members:
        parts = m.name.split('/', 1)
        if len(parts) < 2 or not parts[1]:
            continue  # skip top-level dir entry itself
        m.name = parts[1]
        t.extract(m, dst)
        extracted += 1
        if extracted % 1000 == 0:
            print(f'  Extracted {extracted}/{len(members)}...')

print(f'Done. Extracted {extracted} files to {dst}')

# List top-level contents
print('\nContents of cn_data:')
for item in sorted(os.listdir(dst)):
    print(f'  {item}/')
