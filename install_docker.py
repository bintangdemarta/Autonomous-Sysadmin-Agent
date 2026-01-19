#!/usr/bin/env python3
"""
Script to install Docker on the server and update the web application with container management features
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

def install_docker(ssh_client):
    """
    Install Docker on the server
    """
    print("Checking if Docker is installed...")
    
    # Check if Docker is already installed
    stdin, stdout, stderr = ssh_client.exec_command('command -v docker')
    output = stdout.read().decode().strip()
    
    if output:
        print(f"Docker is already installed at: {output}")
        
        # Get Docker version
        stdin, stdout, stderr = ssh_client.exec_command('docker --version')
        version = stdout.read().decode().strip()
        print(f"Docker version: {version}")
        return True
    else:
        print("Docker is not installed. Installing Docker...")
        
        # Update package index
        print("Updating package index...")
        stdin, stdout, stderr = ssh_client.exec_command('sudo apt update', get_pty=True)
        stdin.write(os.getenv('PROXMOX_PASSWORD') + '\n')
        stdin.flush()
        exit_status = stdout.channel.recv_exit_status()
        print(f"Package update completed with exit status: {exit_status}")
        
        # Install prerequisites
        print("Installing prerequisites...")
        stdin, stdout, stderr = ssh_client.exec_command('sudo apt install -y ca-certificates curl gnupg lsb-release', get_pty=True)
        stdin.write(os.getenv('PROXMOX_PASSWORD') + '\n')
        stdin.flush()
        exit_status = stdout.channel.recv_exit_status()
        print(f"Prerequisites installation completed with exit status: {exit_status}")
        
        # Add Docker's official GPG key
        print("Adding Docker's official GPG key...")
        stdin, stdout, stderr = ssh_client.exec_command('sudo mkdir -p /etc/apt/keyrings && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg', get_pty=True)
        stdin.write(os.getenv('PROXMOX_PASSWORD') + '\n')
        stdin.flush()
        exit_status = stdout.channel.recv_exit_status()
        print(f"GPG key addition completed with exit status: {exit_status}")
        
        # Set up the repository
        print("Setting up Docker repository...")
        stdin, stdout, stderr = ssh_client.exec_command('echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null', get_pty=True)
        stdin.write(os.getenv('PROXMOX_PASSWORD') + '\n')
        stdin.flush()
        exit_status = stdout.channel.recv_exit_status()
        print(f"Repository setup completed with exit status: {exit_status}")
        
        # Update package index again
        print("Updating package index after adding Docker repo...")
        stdin, stdout, stderr = ssh_client.exec_command('sudo apt update', get_pty=True)
        stdin.write(os.getenv('PROXMOX_PASSWORD') + '\n')
        stdin.flush()
        exit_status = stdout.channel.recv_exit_status()
        print(f"Package update completed with exit status: {exit_status}")
        
        # Install Docker Engine
        print("Installing Docker Engine...")
        stdin, stdout, stderr = ssh_client.exec_command('sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin', get_pty=True)
        stdin.write(os.getenv('PROXMOX_PASSWORD') + '\n')
        stdin.flush()
        exit_status = stdout.channel.recv_exit_status()
        print(f"Docker installation completed with exit status: {exit_status}")
        
        # Add user to docker group
        print("Adding user to docker group...")
        stdin, stdout, stderr = ssh_client.exec_command(f'sudo usermod -aG docker {os.getenv("PROXMOX_USER", "bintangdmrt")}', get_pty=True)
        stdin.write(os.getenv('PROXMOX_PASSWORD') + '\n')
        stdin.flush()
        exit_status = stdout.channel.recv_exit_status()
        print(f"User added to docker group with exit status: {exit_status}")
        
        # Start and enable Docker service
        print("Starting and enabling Docker service...")
        stdin, stdout, stderr = ssh_client.exec_command('sudo systemctl start docker && sudo systemctl enable docker', get_pty=True)
        stdin.write(os.getenv('PROXMOX_PASSWORD') + '\n')
        stdin.flush()
        exit_status = stdout.channel.recv_exit_status()
        print(f"Docker service start/enabled with exit status: {exit_status}")
        
        # Verify installation
        stdin, stdout, stderr = ssh_client.exec_command('docker --version')
        version = stdout.read().decode().strip()
        print(f"Docker installed successfully: {version}")
        
        # Test Docker
        stdin, stdout, stderr = ssh_client.exec_command('docker run hello-world')
        output = stdout.read().decode()
        error = stderr.read().decode()
        print(f"Docker test run output: {output}")
        if error:
            print(f"Docker test run error: {error}")
        
        return True

def main():
    """
    Main function to install Docker
    """
    print("Installing Docker on the server...")
    
    # Connect to the server
    ssh_client = connect_to_server()
    if not ssh_client:
        print("Failed to connect to the server. Exiting.")
        sys.exit(1)
    
    try:
        # Install Docker
        install_docker(ssh_client)
        
        print("\nDocker has been successfully installed on the server!")
        print("The user has been added to the docker group.")
        print("Docker service is running and enabled.")
        
    except Exception as e:
        print(f"An error occurred during Docker installation: {str(e)}")
    finally:
        ssh_client.close()
        print("SSH connection closed.")

if __name__ == "__main__":
    main()