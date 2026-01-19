#!/usr/bin/env python3
"""
Deployment script to install a web server and deploy the application to the Proxmox server via SSH
"""

import paramiko
import os
import sys
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

def connect_to_server():
    """
    Connect to the Proxmox server via SSH using credentials from environment variables
    """
    # Get credentials from environment variables
    host = os.getenv('PROXMOX_HOST', '100.124.247.81')  # Default to the new Tailscale IP
    user = os.getenv('PROXMOX_USER')
    password = os.getenv('PROXMOX_PASSWORD')

    # Validate that all credentials are present
    if not all([host, user, password]):
        raise ValueError("Missing required environment variables for Proxmox connection")

    # Create SSH client
    ssh_client = paramiko.SSHClient()

    # Automatically add the server's host key (this is insecure in production)
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the Proxmox server
        print(f"Connecting to {host}...")
        ssh_client.connect(hostname=host, username=user, password=password)
        print(f"Successfully connected to {host}")

        return ssh_client

    except Exception as e:
        print(f"Failed to connect to Proxmox server: {str(e)}")
        return None

def install_web_server(ssh_client):
    """
    Install necessary packages for running the web application
    """
    print("Installing web server dependencies...")
    
    # Update package list
    stdin, stdout, stderr = ssh_client.exec_command('sudo apt update')
    stdout.channel.recv_exit_status()  # Wait for command to complete
    
    # Install Python, pip, and other necessary packages
    commands = [
        'sudo apt install -y python3 python3-pip python3-dev',
        'sudo apt install -y build-essential libssl-dev libffi-dev',
        'sudo apt install -y nginx supervisor',
        'sudo apt install -y git'
    ]
    
    for cmd in commands:
        print(f"Running: {cmd}")
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        
        # Print output in real-time
        for line in iter(stdout.readline, ""):
            print(line.strip())
            
        # Check for errors
        stderr_output = stderr.read().decode()
        if stderr_output:
            print(f"Error: {stderr_output}")
        
        # Wait for command to complete
        exit_status = stdout.channel.recv_exit_status()
        print(f"Command completed with exit status: {exit_status}")

def upload_application(ssh_client):
    """
    Upload the application files to the server
    """
    print("Uploading application files...")
    
    # Create directory for the application
    stdin, stdout, stderr = ssh_client.exec_command('mkdir -p ~/nexus-cli')
    stdout.channel.recv_exit_status()
    
    # Use SFTP to upload files
    sftp = ssh_client.open_sftp()
    
    # Local paths
    local_paths = [
        'ssh_connect_example.py',
        'test_functionality.py',
        'test_setup.py',
        'requirements.txt',
        'config/commands.json',
        'web/app.py',
        'web/requirements.txt',
        'web/templates/index.html',
        'web/templates/commands.html',
        'web/static/'  # if it exists
    ]
    
    # Upload each file
    for local_path in local_paths:
        local_full_path = os.path.join(os.getcwd(), local_path)
        remote_path = f'~/nexus-cli/{local_path}'
        
        if os.path.exists(local_full_path):
            if os.path.isfile(local_full_path):
                print(f"Uploading {local_path}...")
                # Create remote directory if it doesn't exist
                remote_dir = os.path.dirname(remote_path)
                stdin, stdout, stderr = ssh_client.exec_command(f'mkdir -p {remote_dir}')
                stdout.channel.recv_exit_status()
                
                sftp.put(local_full_path, remote_path)
            elif os.path.isdir(local_full_path):
                # Recursively upload directory
                upload_directory(sftp, local_full_path, f'~/nexus-cli/{local_path}', ssh_client)
    
    sftp.close()
    print("Application files uploaded successfully!")

def upload_directory(sftp, local_dir, remote_dir, ssh_client):
    """
    Recursively upload a directory to the server
    """
    # Create remote directory
    stdin, stdout, stderr = ssh_client.exec_command(f'mkdir -p {remote_dir}')
    stdout.channel.recv_exit_status()
    
    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        remote_path = f'{remote_dir}/{item}'
        
        if os.path.isfile(local_path):
            print(f"Uploading {local_path}...")
            sftp.put(local_path, remote_path)
        elif os.path.isdir(local_path):
            upload_directory(sftp, local_path, remote_path, ssh_client)

def setup_python_environment(ssh_client):
    """
    Set up Python virtual environment and install dependencies
    """
    print("Setting up Python environment...")
    
    # Create virtual environment
    stdin, stdout, stderr = ssh_client.exec_command('cd ~/nexus-cli && python3 -m venv venv')
    exit_status = stdout.channel.recv_exit_status()
    print(f"Virtual environment created with exit status: {exit_status}")
    
    # Install dependencies
    cmd = 'cd ~/nexus-cli && source venv/bin/activate && pip install --upgrade pip && pip install -r web/requirements.txt'
    stdin, stdout, stderr = ssh_client.exec_command(cmd)
    
    print("Installing Python dependencies...")
    # Print output in real-time
    for line in iter(stdout.readline, ""):
        print(line.strip())
        
    exit_status = stdout.channel.recv_exit_status()
    print(f"Dependencies installed with exit status: {exit_status}")

def setup_supervisor(ssh_client):
    """
    Configure Supervisor to run the Flask application
    """
    print("Setting up Supervisor configuration...")
    
    # Create Supervisor configuration file
    supervisor_conf = '''[program:nexus-cli-web]
command=/home/%(ENV_PROXMOX_USER)s/nexus-cli/venv/bin/python /home/%(ENV_PROXMOX_USER)s/nexus-cli/web/app.py
directory=/home/%(ENV_PROXMOX_USER)s/nexus-cli
user=%(ENV_PROXMOX_USER)s
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/nexus-cli-web.log
'''
    
    # Write the configuration to a temporary file and then move it to the correct location
    sftp = ssh_client.open_sftp()
    
    # Write to a temporary location first
    temp_conf_path = '/tmp/nexus-cli-web.conf'
    with sftp.open(temp_conf_path, 'w') as f:
        f.write(supervisor_conf)
    
    # Move to the Supervisor configuration directory (requires sudo)
    stdin, stdout, stderr = ssh_client.exec_command(f'sudo mv {temp_conf_path} /etc/supervisor/conf.d/nexus-cli-web.conf')
    exit_status = stdout.channel.recv_exit_status()
    print(f"Supervisor config moved with exit status: {exit_status}")
    
    # Reload Supervisor
    stdin, stdout, stderr = ssh_client.exec_command('sudo supervisorctl reread')
    stdout.channel.recv_exit_status()
    
    stdin, stdout, stderr = ssh_client.exec_command('sudo supervisorctl update')
    exit_status = stdout.channel.recv_exit_status()
    print(f"Supervisor reloaded with exit status: {exit_status}")
    
    sftp.close()

def setup_nginx(ssh_client):
    """
    Configure Nginx as a reverse proxy for the Flask application
    """
    print("Setting up Nginx configuration...")
    
    # Get the actual username for the config
    stdin, stdout, stderr = ssh_client.exec_command('echo $USER')
    username = stdout.read().decode().strip()
    
    nginx_conf = f'''server {{
    listen 80;
    server_name _;

    location / {{
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
'''
    
    # Write the configuration to a temporary file and then move it to the correct location
    sftp = ssh_client.open_sftp()
    
    # Write to a temporary location first
    temp_conf_path = '/tmp/nexus-cli-web'
    with sftp.open(temp_conf_path, 'w') as f:
        f.write(nginx_conf)
    
    # Move to the Nginx sites-available directory (requires sudo)
    stdin, stdout, stderr = ssh_client.exec_command(f'sudo mv {temp_conf_path} /etc/nginx/sites-available/nexus-cli-web')
    exit_status = stdout.channel.recv_exit_status()
    print(f"Nginx config moved with exit status: {exit_status}")
    
    # Enable the site by creating a symbolic link
    stdin, stdout, stderr = ssh_client.exec_command('sudo ln -s /etc/nginx/sites-available/nexus-cli-web /etc/nginx/sites-enabled/')
    exit_status = stdout.channel.recv_exit_status()
    print(f"Site enabled with exit status: {exit_status}")
    
    # Remove default site to avoid conflicts
    stdin, stdout, stderr = ssh_client.exec_command('sudo rm -f /etc/nginx/sites-enabled/default')
    exit_status = stdout.channel.recv_exit_status()
    
    # Test Nginx configuration
    stdin, stdout, stderr = ssh_client.exec_command('sudo nginx -t')
    exit_status = stdout.channel.recv_exit_status()
    print(f"Nginx config test result: {exit_status}")
    
    # Restart Nginx
    stdin, stdout, stderr = ssh_client.exec_command('sudo systemctl restart nginx')
    exit_status = stdout.channel.recv_exit_status()
    print(f"Nginx restarted with exit status: {exit_status}")
    
    sftp.close()

def start_application(ssh_client):
    """
    Start the web application using Supervisor
    """
    print("Starting the web application...")
    
    # Start the application via Supervisor
    stdin, stdout, stderr = ssh_client.exec_command('sudo supervisorctl start nexus-cli-web')
    exit_status = stdout.channel.recv_exit_status()
    print(f"Application started with exit status: {exit_status}")
    
    # Check the status
    stdin, stdout, stderr = ssh_client.exec_command('sudo supervisorctl status nexus-cli-web')
    status = stdout.read().decode()
    print(f"Application status: {status}")

def main():
    """
    Main deployment function
    """
    print("Starting deployment of Nexus-CLI web application...")
    
    # Connect to the server
    ssh_client = connect_to_server()
    if not ssh_client:
        print("Failed to connect to the server. Exiting.")
        sys.exit(1)
    
    try:
        # Install web server dependencies
        install_web_server(ssh_client)
        
        # Upload application files
        upload_application(ssh_client)
        
        # Set up Python environment
        setup_python_environment(ssh_client)
        
        # Set up Supervisor
        setup_supervisor(ssh_client)
        
        # Set up Nginx
        setup_nginx(ssh_client)
        
        # Start the application
        start_application(ssh_client)
        
        print("\nDeployment completed successfully!")
        print("The web application should now be accessible via the server's IP address.")
        
    except Exception as e:
        print(f"An error occurred during deployment: {str(e)}")
    finally:
        ssh_client.close()
        print("SSH connection closed.")

if __name__ == "__main__":
    main()