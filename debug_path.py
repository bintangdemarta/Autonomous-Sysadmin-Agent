import os

# Test path construction
local_path = 'web/app.py'
script_dir = os.path.dirname(os.path.abspath(__file__))
local_full_path = os.path.join(script_dir, local_path)

print(f'Script directory: {script_dir}')
print(f'Local path: {local_path}')
print(f'Local full path: {local_full_path}')
print(f'File exists: {os.path.exists(local_full_path)}')

# List files in web directory
web_dir = os.path.join(script_dir, 'web')
print(f'\nFiles in web directory:')
for f in os.listdir(web_dir):
    print(f'  {f}')