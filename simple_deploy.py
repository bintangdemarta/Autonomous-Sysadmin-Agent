#!/usr/bin/env python3
"""
Simple deployment script to install a web server and deploy the application to the Proxmox server via SSH
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
        ssh_client.connect(hostname=host, username=user, password=password, timeout=10)
        print(f"Successfully connected to {host}")

        return ssh_client

    except Exception as e:
        print(f"Failed to connect to Proxmox server: {str(e)}")
        return None

def run_commands(ssh_client, commands, description="", use_sudo_password=False):
    """
    Execute a series of commands on the remote server
    """
    print(f"{description}")
    for cmd in commands:
        print(f"  Running: {cmd}")

        # If using sudo with password, we need to use pty
        if 'sudo' in cmd and use_sudo_password:
            stdin, stdout, stderr = ssh_client.exec_command(cmd, get_pty=True)
            stdin.write(os.getenv('PROXMOX_PASSWORD') + '\n')
            stdin.flush()
        else:
            stdin, stdout, stderr = ssh_client.exec_command(cmd)

        # Print output
        output = stdout.read().decode()
        error = stderr.read().decode()

        if output:
            print(f"    Output: {output.strip()}")
        if error:
            print(f"    Error: {error.strip()}")

        # Wait for command to complete
        exit_status = stdout.channel.recv_exit_status()
        print(f"    Exit status: {exit_status}")

    print("Commands completed.\n")

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

    # Define local paths to upload
    local_paths = [
        ('requirements.txt', '~/nexus-cli/requirements.txt'),
        ('config/commands.json', '~/nexus-cli/config/commands.json'),
        ('web/app.py', '~/nexus-cli/web/app.py'),
        ('web/requirements.txt', '~/nexus-cli/web/requirements.txt'),
    ]

    # Upload each file
    for local_path, remote_path in local_paths:
        local_full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), local_path)
        if os.path.exists(local_full_path):
            print(f"  Uploading {local_path} to {remote_path}...")
            # Create remote directory if it doesn't exist
            remote_dir = os.path.dirname(remote_path)
            stdin, stdout, stderr = ssh_client.exec_command(f'mkdir -p {remote_dir}')
            stdout.channel.recv_exit_status()

            sftp.put(local_full_path, remote_path)
        else:
            print(f"  Warning: {local_path} does not exist, skipping...")

    # Also upload template files
    template_paths = [
        ('web/templates/index.html', '~/nexus-cli/web/templates/index.html'),
        ('web/templates/commands.html', '~/nexus-cli/web/templates/commands.html'),
    ]

    for local_path, remote_path in template_paths:
        local_full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), local_path)
        if os.path.exists(local_full_path):
            print(f"  Uploading {local_path} to {remote_path}...")
            remote_dir = os.path.dirname(remote_path)
            stdin, stdout, stderr = ssh_client.exec_command(f'mkdir -p {remote_dir}')
            stdout.channel.recv_exit_status()

            sftp.put(local_full_path, remote_path)
        else:
            print(f"  Warning: {local_path} does not exist, skipping...")

    sftp.close()
    print("Application files uploaded successfully!\n")

def main():
    """
    Main deployment function
    """
    print("Starting deployment of Nexus-CLI web application...")
    print("This will:")
    print("  1. Install necessary packages (Python, pip, nginx)")
    print("  2. Upload application files")
    print("  3. Set up Python virtual environment")
    print("  4. Configure and start the web server")
    
    # Connect to the server
    ssh_client = connect_to_server()
    if not ssh_client:
        print("Failed to connect to the server. Exiting.")
        sys.exit(1)
    
    try:
        # Update package list and install necessary packages
        update_and_install_cmds = [
            'sudo -S apt update',
            'sudo -S apt install -y python3 python3-pip python3-venv',
            'sudo -S apt install -y nginx',
            'sudo -S apt install -y curl'
        ]
        run_commands(ssh_client, update_and_install_cmds, "Updating system and installing packages...", use_sudo_password=True)
        
        # Upload application files
        upload_application(ssh_client)
        
        # Set up Python virtual environment and install dependencies
        setup_python_cmds = [
            'cd ~/nexus-cli && python3 -m venv venv',
            'cd ~/nexus-cli && source venv/bin/activate && pip install --upgrade pip',
            'cd ~/nexus-cli && source venv/bin/activate && pip install -r requirements.txt',
            'cd ~/nexus-cli && source venv/bin/activate && pip install -r web/requirements.txt'
        ]
        run_commands(ssh_client, setup_python_cmds, "Setting up Python environment...")
        
        # Create a systemd service file for the web application
        service_content = '''[Unit]
Description=Nexus-CLI Web Application
After=network.target

[Service]
Type=simple
User=%i
WorkingDirectory=/home/%i/nexus-cli
Environment=PATH=/home/%i/nexus-cli/venv/bin
ExecStart=/home/%i/nexus-cli/venv/bin/python web/app.py
Restart=always

[Install]
WantedBy=multi-user.target
'''.replace('%i', os.getenv('PROXMOX_USER', 'bintangdmrt'))
        
        # Write the service file
        sftp = ssh_client.open_sftp()
        temp_service_path = '/tmp/nexus-cli-web.service'
        with sftp.open(temp_service_path, 'w') as f:
            f.write(service_content)
        sftp.close()
        
        # Move the service file to the correct location
        service_move_cmd = f'sudo mv /tmp/nexus-cli-web.service /etc/systemd/system/nexus-cli-web.service'
        stdin, stdout, stderr = ssh_client.exec_command(service_move_cmd)
        exit_status = stdout.channel.recv_exit_status()
        print(f"Service file moved with exit status: {exit_status}")
        
        # Reload systemd and start the service
        systemd_cmds = [
            'sudo -S systemctl daemon-reload',
            'sudo -S systemctl enable nexus-cli-web.service',
            'sudo -S systemctl start nexus-cli-web.service',
            'sudo -S systemctl status nexus-cli-web.service'
        ]
        run_commands(ssh_client, systemd_cmds, "Setting up and starting the web service...", use_sudo_password=True)
        
        # Configure Nginx as reverse proxy
        nginx_config = f'''server {{
    listen 80;
    server_name {os.getenv('PROXMOX_HOST', '100.124.247.81')};

    location / {{
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
'''
        
        # Write the nginx config
        sftp = ssh_client.open_sftp()
        temp_nginx_path = '/tmp/nexus-cli-web-config'
        with sftp.open(temp_nginx_path, 'w') as f:
            f.write(nginx_config)
        sftp.close()
        
        # Move the nginx config file to the correct location
        nginx_move_cmd = 'sudo mv /tmp/nexus-cli-web-config /etc/nginx/sites-available/nexus-cli-web'
        stdin, stdout, stderr = ssh_client.exec_command(nginx_move_cmd)
        exit_status = stdout.channel.recv_exit_status()
        print(f"Nginx config moved with exit status: {exit_status}")
        
        # Enable the site
        enable_site_cmds = [
            'sudo -S ln -s /etc/nginx/sites-available/nexus-cli-web /etc/nginx/sites-enabled/',
            'sudo -S rm -f /etc/nginx/sites-enabled/default',  # Remove default site
            'sudo -S nginx -t',  # Test nginx config
            'sudo -S systemctl restart nginx'
        ]
        run_commands(ssh_client, enable_site_cmds, "Configuring and restarting Nginx...", use_sudo_password=True)
        
        print("\nDeployment completed successfully!")
        print(f"The web application should now be accessible at http://{os.getenv('PROXMOX_HOST', '100.124.247.81')}")
        print("Service status:")
        stdin, stdout, stderr = ssh_client.exec_command('sudo systemctl status nexus-cli-web')
        print(stdout.read().decode())
        
    except Exception as e:
        print(f"An error occurred during deployment: {str(e)}")
    finally:
        ssh_client.close()
        print("SSH connection closed.")

if __name__ == "__main__":
    main()