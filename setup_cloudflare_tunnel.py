#!/usr/bin/env python3
"""
Script to install and configure Cloudflare Tunnel for secure access to the web application
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

def install_cloudflared(ssh_client):
    """
    Install Cloudflared on the server
    """
    print("Installing Cloudflared...")
    
    # Download and install cloudflared
    commands = [
        'curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb',
        'sudo dpkg -i cloudflared.deb',
        'rm cloudflared.deb'
    ]
    
    for cmd in commands:
        print(f"  Running: {cmd}")
        stdin, stdout, stderr = ssh_client.exec_command(cmd, get_pty=True)
        stdin.write(os.getenv('PROXMOX_PASSWORD') + '\n')
        stdin.flush()
        
        # Get output
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        if output:
            print(f"    Output: {output[-500:] if len(output) > 500 else output}")
        if error:
            print(f"    Error: {error}")
        
        # Wait for command to complete
        exit_status = stdout.channel.recv_exit_status()
        print(f"    Exit status: {exit_status}")
    
    # Verify installation
    stdin, stdout, stderr = ssh_client.exec_command('cloudflared --version')
    version_output = stdout.read().decode().strip()
    if version_output:
        print(f"Cloudflared installed successfully. Version: {version_output}")
        return True
    else:
        print("Failed to install Cloudflared")
        return False

def setup_cloudflared_tunnel(ssh_client):
    """
    Set up Cloudflare Tunnel to expose the web application
    """
    print("Setting up Cloudflare Tunnel...")
    
    # Login to Cloudflare (this will require user interaction)
    print("You will need to authenticate with Cloudflare in the next step.")
    print("A browser window will open for authentication.")
    
    # Run login command
    stdin, stdout, stderr = ssh_client.exec_command('cloudflared tunnel login')
    
    # The login process will generate a URL that needs to be visited
    # In a real scenario, we would need to handle this differently
    # For now, let's just create a tunnel configuration
    
    # Create a tunnel
    tunnel_name = "nexus-cli-tunnel"
    stdin, stdout, stderr = ssh_client.exec_command(f'cloudflared tunnel create {tunnel_name}')
    
    output = stdout.read().decode()
    error = stderr.read().decode()
    
    print(f"Tunnel creation output: {output}")
    if error:
        print(f"Tunnel creation error: {error}")
    
    # Create configuration directory
    stdin, stdout, stderr = ssh_client.exec_command('mkdir -p ~/.cloudflared')
    stdout.channel.recv_exit_status()
    
    # Create configuration file for the tunnel
    config_content = f'''ingress:
  - hostname: nexus-cli.yourdomain.com
    service: http://localhost:5000
  - service: http_status:404
'''
    
    # Write config to a temporary file and move to the right location
    sftp = ssh_client.open_sftp()
    temp_config_path = '/tmp/config.yml'
    with sftp.open(temp_config_path, 'w') as f:
        f.write(config_content)
    sftp.close()
    
    # Move config to the correct location
    stdin, stdout, stderr = ssh_client.exec_command('mkdir -p ~/.cloudflared && mv /tmp/config.yml ~/.cloudflared/config.yml')
    exit_status = stdout.channel.recv_exit_status()
    print(f"Configuration file created with exit status: {exit_status}")
    
    # Create a systemd service for the tunnel
    service_content = f'''[Unit]
Description=Cloudflared Tunnel
After=network.target

[Service]
Type=simple
User={os.getenv("PROXMOX_USER", "bintangdmrt")}
ExecStart=/usr/local/bin/cloudflared tunnel --config /home/{os.getenv("PROXMOX_USER", "bintangdmrt")}/.cloudflared/config.yml run
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
'''
    
    # Write the service file
    sftp = ssh_client.open_sftp()
    temp_service_path = '/tmp/cloudflared-tunnel.service'
    with sftp.open(temp_service_path, 'w') as f:
        f.write(service_content)
    sftp.close()
    
    # Move the service file to the correct location (using sudo)
    stdin, stdout, stderr = ssh_client.exec_command('sudo mv /tmp/cloudflared-tunnel.service /etc/systemd/system/cloudflared-tunnel.service', get_pty=True)
    stdin.write(os.getenv('PROXMOX_PASSWORD') + '\n')
    stdin.flush()
    exit_status = stdout.channel.recv_exit_status()
    print(f"Service file moved with exit status: {exit_status}")
    
    # Enable and start the service
    commands = [
        'sudo systemctl daemon-reload',
        'sudo systemctl enable cloudflared-tunnel.service',
        'sudo systemctl start cloudflared-tunnel.service'
    ]
    
    for cmd in commands:
        print(f"  Running: {cmd}")
        stdin, stdout, stderr = ssh_client.exec_command(cmd, get_pty=True)
        stdin.write(os.getenv('PROXMOX_PASSWORD') + '\n')
        stdin.flush()
        
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        if output:
            print(f"    Output: {output}")
        if error:
            print(f"    Error: {error}")
        
        exit_status = stdout.channel.recv_exit_status()
        print(f"    Exit status: {exit_status}")
    
    # Check tunnel status
    stdin, stdout, stderr = ssh_client.exec_command('sudo systemctl status cloudflared-tunnel.service')
    status = stdout.read().decode()
    print(f"Tunnel service status: {'running' if 'active (running)' in status else 'not running'}")
    
    print("\nCloudflare Tunnel setup completed!")
    print("Note: You'll need to update your domain's DNS settings to point to the tunnel.")
    print("Run 'cloudflared tunnel info' to get the tunnel ID and CNAME records.")

def main():
    """
    Main function to install and configure Cloudflare Tunnel
    """
    print("Setting up Cloudflare Tunnel for secure access to the web application...")
    print("This will:")
    print("  1. Install Cloudflared")
    print("  2. Create a tunnel configuration")
    print("  3. Set up a systemd service to run the tunnel")
    
    # Connect to the server
    ssh_client = connect_to_server()
    if not ssh_client:
        print("Failed to connect to the server. Exiting.")
        sys.exit(1)
    
    try:
        # Install cloudflared
        if install_cloudflared(ssh_client):
            print("\nProceeding with tunnel configuration...")
            setup_cloudflared_tunnel(ssh_client)
        else:
            print("\nCannot proceed with tunnel setup due to installation failure.")
    
    except Exception as e:
        print(f"An error occurred during Cloudflare Tunnel setup: {str(e)}")
    finally:
        ssh_client.close()
        print("SSH connection closed.")

if __name__ == "__main__":
    main()