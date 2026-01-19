import os

# Test path construction
script_dir = os.getcwd()  # Current working directory
local_path = 'web/app.py'
local_full_path = os.path.normpath(os.path.join(script_dir, local_path))

print(f'Script dir: {script_dir}')
print(f'Local path: {local_path}')
print(f'Full path: {local_full_path}')
print(f'Exists: {os.path.exists(local_full_path)}')

# Check if individual parts exist
print(f'CWD exists: {os.path.exists(script_dir)}')
print('web dir exists:', os.path.exists(os.path.join(script_dir, "web")))
print('app.py in web exists:', os.path.exists(os.path.join(script_dir, "web", "app.py")))

# List web directory
if os.path.exists(os.path.join(script_dir, "web")):
    print('Contents of web:', os.listdir(os.path.join(script_dir, "web")))