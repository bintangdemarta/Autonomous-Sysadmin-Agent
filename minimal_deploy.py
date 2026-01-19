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

def run_command_with_sudo(ssh_client, command, description=""):
    """
    Execute a command with sudo privileges
    """
    print(f"{description}")
    print(f"  Running: {command}")
    
    # Use get_pty=True to allocate a pseudo-terminal for sudo
    stdin, stdout, stderr = ssh_client.exec_command(command, get_pty=True)
    
    # Write the password to stdin for sudo
    stdin.write(os.getenv('PROXMOX_PASSWORD') + '\n')
    stdin.flush()
    
    # Get output and error
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    
    # Wait for command to complete
    exit_status = stdout.channel.recv_exit_status()
    
    if output:
        print(f"    Output: {output[-500:] if len(output) > 500 else output}")  # Show last 500 chars to avoid overflow
    if error:
        print(f"    Error: {error}")
    
    print(f"    Exit status: {exit_status}")
    return exit_status

def upload_file(ssh_client, local_path, remote_path):
    """
    Upload a single file to the remote server
    """
    # Use SFTP to upload the file
    sftp = ssh_client.open_sftp()
    
    # Create remote directory if it doesn't exist
    remote_dir = os.path.dirname(remote_path)
    stdin, stdout, stderr = ssh_client.exec_command(f'mkdir -p {remote_dir}')
    stdout.channel.recv_exit_status()
    
    try:
        sftp.put(local_path, remote_path)
        print(f"  Uploaded {local_path} to {remote_path}")
    except FileNotFoundError:
        print(f"  Warning: {local_path} does not exist, skipping...")
    
    sftp.close()

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
        # Update package list
        run_command_with_sudo(ssh_client, 'apt update', "Updating package list...")
        
        # Install necessary packages
        run_command_with_sudo(ssh_client, 'apt install -y python3 python3-pip python3-venv nginx git', 
                             "Installing required packages...")
        
        # Create directory for the application
        stdin, stdout, stderr = ssh_client.exec_command('mkdir -p ~/nexus-cli')
        stdout.channel.recv_exit_status()
        
        # Upload application files
        print("Uploading application files...")
        
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
                upload_file(ssh_client, local_full_path, remote_path)
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
                upload_file(ssh_client, local_full_path, remote_path)
            else:
                print(f"  Warning: {local_path} does not exist, skipping...")
        
        print("Application files uploaded successfully!\n")
        
        # Set up Python virtual environment and install dependencies
        print("Setting up Python virtual environment...")
        
        # Create virtual environment
        stdin, stdout, stderr = ssh_client.exec_command('cd ~/nexus-cli && python3 -m venv venv')
        exit_status = stdout.channel.recv_exit_status()
        print(f"Virtual environment created with exit status: {exit_status}")
        
        # Install dependencies
        print("Installing Python dependencies...")
        stdin, stdout, stderr = ssh_client.exec_command('cd ~/nexus-cli && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt && pip install -r web/requirements.txt')
        exit_status = stdout.channel.recv_exit_status()
        print(f"Dependencies installed with exit status: {exit_status}")
        
        # Create a systemd service file for the web application
        print("Creating systemd service...")
        
        service_content = f'''[Unit]
Description=Nexus-CLI Web Application
After=network.target

[Service]
Type=simple
User={os.getenv("PROXMOX_USER", "bintangdmrt")}
WorkingDirectory=/home/{os.getenv("PROXMOX_USER", "bintangdmrt")}/nexus-cli
Environment=PATH=/home/{os.getenv("PROXMOX_USER", "bintangdmrt")}/nexus-cli/venv/bin
ExecStart=/home/{os.getenv("PROXMOX_USER", "bintangdmrt")}/nexus-cli/venv/bin/python web/app.py
Restart=always

[Install]
WantedBy=multi-user.target
'''
        
        # Write the service file using SFTP
        sftp = ssh_client.open_sftp()
        temp_service_path = '/tmp/nexus-cli-web.service'
        with sftp.open(temp_service_path, 'w') as f:
            f.write(service_content)
        sftp.close()
        
        # Move the service file to the correct location
        run_command_with_sudo(ssh_client, f'mv /tmp/nexus-cli-web.service /etc/systemd/system/nexus-cli-web.service', 
                             "Moving service file...")
        
        # Reload systemd and start the service
        run_command_with_sudo(ssh_client, 'systemctl daemon-reload', "Reloading systemd...")
        run_command_with_sudo(ssh_client, 'systemctl enable nexus-cli-web.service', "Enabling service...")
        run_command_with_sudo(ssh_client, 'systemctl start nexus-cli-web.service', "Starting service...")
        
        # Configure Nginx as reverse proxy
        print("Configuring Nginx...")
        
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
        
        # Write the nginx config using SFTP
        sftp = ssh_client.open_sftp()
        temp_nginx_path = '/tmp/nexus-cli-web-config'
        with sftp.open(temp_nginx_path, 'w') as f:
            f.write(nginx_config)
        sftp.close()
        
        # Move the nginx config file to the correct location
        run_command_with_sudo(ssh_client, 'mv /tmp/nexus-cli-web-config /etc/nginx/sites-available/nexus-cli-web', 
                             "Moving Nginx config...")
        
        # Enable the site
        run_command_with_sudo(ssh_client, 'ln -s /etc/nginx/sites-available/nexus-cli-web /etc/nginx/sites-enabled/', 
                             "Enabling Nginx site...")
        run_command_with_sudo(ssh_client, 'rm -f /etc/nginx/sites-enabled/default', 
                             "Removing default Nginx site...")
        run_command_with_sudo(ssh_client, 'nginx -t', 
                             "Testing Nginx config...")
        run_command_with_sudo(ssh_client, 'systemctl restart nginx', 
                             "Restarting Nginx...")
        
        print("\nDeployment completed successfully!")
        print(f"The web application should now be accessible at http://{os.getenv('PROXMOX_HOST', '100.124.247.81')}")
        
        # Check service status
        stdin, stdout, stderr = ssh_client.exec_command('systemctl status nexus-cli-web')
        status_output = stdout.read().decode('utf-8', errors='ignore')
        print(f"Service status: {'running' if 'active (running)' in status_output else 'not running'}")
        
    except Exception as e:
        print(f"An error occurred during deployment: {str(e)}")
    finally:
        ssh_client.close()
        print("SSH connection closed.")

if __name__ == "__main__":
    main()