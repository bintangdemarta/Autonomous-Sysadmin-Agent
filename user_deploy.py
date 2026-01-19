#!/usr/bin/env python3
"""
Simple deployment script to run the web application on the Proxmox server via SSH
This version runs the application as a regular user without requiring sudo privileges
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

def upload_file(ssh_client, local_path, remote_path):
    """
    Upload a single file to the remote server
    """
    try:
        # Use SFTP to upload the file
        sftp = ssh_client.open_sftp()

        # Create remote directory if it doesn't exist
        remote_dir = os.path.dirname(remote_path)
        stdin, stdout, stderr = ssh_client.exec_command(f'mkdir -p {remote_dir}')
        # Wait for the command to complete
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            print(f"  Error creating directory {remote_dir}. Exit status: {exit_status}")

        # Upload the file
        sftp.put(local_path, remote_path)
        print(f"  Uploaded {local_path} to {remote_path}")

        sftp.close()
    except Exception as e:
        print(f"  Error uploading {local_path} to {remote_path}: {str(e)}")

def main():
    """
    Main deployment function
    """
    print("Starting deployment of Nexus-CLI web application...")
    print("This will:")
    print("  1. Upload application files to user directory")
    print("  2. Set up Python virtual environment")
    print("  3. Run the web application on port 5000")
    
    # Connect to the server
    ssh_client = connect_to_server()
    if not ssh_client:
        print("Failed to connect to the server. Exiting.")
        sys.exit(1)
    
    try:
        # Create directory for the application
        stdin, stdout, stderr = ssh_client.exec_command('mkdir -p /home/bintangdmrt/nexus-cli')
        stdout.channel.recv_exit_status()
        
        # Upload application files
        print("Uploading application files...")
        
        # Define local paths to upload
        local_paths = [
            ('requirements.txt', '/home/bintangdmrt/nexus-cli/requirements.txt'),
            ('config/commands.json', '/home/bintangdmrt/nexus-cli/config/commands.json'),
            ('web/app.py', '/home/bintangdmrt/nexus-cli/web/app.py'),
            ('web/requirements.txt', '/home/bintangdmrt/nexus-cli/web/requirements.txt'),
        ]
        
        # Upload each file
        script_dir = os.path.dirname(os.path.abspath(__file__))  # Get the directory of the current script
        print(f"Script directory: {script_dir}")
        for local_path, remote_path in local_paths:
            # Use os.path.normpath to normalize the path for the current OS
            local_full_path = os.path.normpath(os.path.join(script_dir, local_path))
            print(f"Checking if {local_full_path} exists: {os.path.exists(local_full_path)}")
            if os.path.exists(local_full_path):
                upload_file(ssh_client, local_full_path, remote_path)
            else:
                print(f"  Warning: {local_path} does not exist at {local_full_path}, skipping...")

        # Also upload template files
        template_paths = [
            ('web/templates/index.html', '/home/bintangdmrt/nexus-cli/web/templates/index.html'),
            ('web/templates/commands.html', '/home/bintangdmrt/nexus-cli/web/templates/commands.html'),
        ]

        for local_path, remote_path in template_paths:
            # Use os.path.normpath to normalize the path for the current OS
            local_full_path = os.path.normpath(os.path.join(script_dir, local_path))
            print(f"Checking if {local_full_path} exists: {os.path.exists(local_full_path)}")
            if os.path.exists(local_full_path):
                upload_file(ssh_client, local_full_path, remote_path)
            else:
                print(f"  Warning: {local_path} does not exist at {local_full_path}, skipping...")
        
        print("Application files uploaded successfully!\n")
        
        # Set up Python virtual environment and install dependencies
        print("Setting up Python virtual environment...")
        
        # Create virtual environment
        stdin, stdout, stderr = ssh_client.exec_command('cd /home/bintangdmrt/nexus-cli && python3 -m venv venv')
        exit_status = stdout.channel.recv_exit_status()
        print(f"Virtual environment created with exit status: {exit_status}")

        # Upgrade pip
        print("Upgrading pip...")
        stdin, stdout, stderr = ssh_client.exec_command('cd /home/bintangdmrt/nexus-cli && source venv/bin/activate && pip install --upgrade pip')
        exit_status = stdout.channel.recv_exit_status()
        print(f"Pip upgraded with exit status: {exit_status}")

        # Install dependencies from the project requirements
        print("Installing Python dependencies...")
        stdin, stdout, stderr = ssh_client.exec_command('cd /home/bintangdmrt/nexus-cli && source venv/bin/activate && pip install flask paramiko colorama python-dotenv')
        exit_status = stdout.channel.recv_exit_status()
        print(f"Dependencies installed with exit status: {exit_status}")

        # Start the web application in the background
        print("Starting the web application...")
        # Use nohup to keep the process running after SSH disconnects
        start_cmd = 'cd /home/bintangdmrt/nexus-cli && source venv/bin/activate && nohup python web/app.py > app.log 2>&1 &'
        stdin, stdout, stderr = ssh_client.exec_command(start_cmd)
        
        # Small delay to let the app start
        time.sleep(3)
        
        # Check if the process is running
        stdin, stdout, stderr = ssh_client.exec_command('ps aux | grep "python web/app.py" | grep -v grep')
        process_output = stdout.read().decode()

        if process_output:
            print("Web application started successfully!")
            print(f"The web application should now be accessible at http://{os.getenv('PROXMOX_HOST', '100.124.247.81')}:5000")
        else:
            print("Failed to start the web application")

        # Show the last few lines of the log file
        print("\nLast 10 lines of application log:")
        stdin, stdout, stderr = ssh_client.exec_command('tail -10 /home/bintangdmrt/nexus-cli/app.log')
        log_output = stdout.read().decode()
        print(log_output)
        
    except Exception as e:
        print(f"An error occurred during deployment: {str(e)}")
    finally:
        ssh_client.close()
        print("SSH connection closed.")

if __name__ == "__main__":
    main()