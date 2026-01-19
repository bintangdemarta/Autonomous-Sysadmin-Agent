#!/usr/bin/env python3
"""
Script to update the web application with container management features
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

def upload_enhanced_app(ssh_client):
    """
    Upload the enhanced web application with container management features
    """
    print("Uploading enhanced web application with container management features...")
    
    # Use SFTP to upload the enhanced app.py file
    sftp = ssh_client.open_sftp()
    
    # Upload the enhanced app.py file from our local file
    local_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'enhanced_app.py')
    remote_app_path = '/home/bintangdmrt/nexus-cli/web/app.py'
    
    print(f"Uploading {local_app_path} to {remote_app_path}...")
    sftp.put(local_app_path, remote_app_path)
    
    sftp.close()
    print("Enhanced application uploaded successfully!")

def restart_application(ssh_client):
    """
    Restart the web application to apply changes
    """
    print("Restarting the web application to apply changes...")
    
    # Kill the existing process
    stdin, stdout, stderr = ssh_client.exec_command('pkill -f "python web/app.py" || true')
    stdout.channel.recv_exit_status()  # Wait for command to complete
    
    # Small delay
    time.sleep(2)
    
    # Start the application again
    start_cmd = 'cd /home/bintangdmrt/nexus-cli && source venv/bin/activate && nohup python web/app.py > app.log 2>&1 &'
    stdin, stdout, stderr = ssh_client.exec_command(start_cmd)
    
    # Small delay to let the app start
    time.sleep(3)
    
    # Check if the process is running
    stdin, stdout, stderr = ssh_client.exec_command('ps aux | grep "python web/app.py" | grep -v grep')
    process_output = stdout.read().decode()
    
    if process_output:
        print("Web application restarted successfully!")
        print(f"The web application should now be accessible at http://{os.getenv('PROXMOX_HOST', '100.124.247.81')}:5000")
        print("It now includes container management features.")
    else:
        print("Could not confirm that the application restarted properly.")

def main():
    """
    Main function to enhance the web application with container management
    """
    print("Enhancing web application with container management features...")
    print("This will:")
    print("  1. Update the app.py with Docker/container management endpoints")
    print("  2. Restart the web application")
    
    # Connect to the server
    ssh_client = connect_to_server()
    if not ssh_client:
        print("Failed to connect to the server. Exiting.")
        sys.exit(1)
    
    try:
        # Upload the enhanced application
        upload_enhanced_app(ssh_client)
        
        # Restart the application to apply changes
        restart_application(ssh_client)
        
        print("\nApplication successfully enhanced with container management features!")
        print("New endpoints added:")
        print("  - GET /containers - List all Docker containers")
        print("  - POST /container/<id>/start - Start a container")
        print("  - POST /container/<id>/stop - Stop a container")
        print("  - POST /container/<id>/restart - Restart a container")
        print("  - POST /container/<id>/remove - Remove a container")
        print("  - POST /container/<id>/logs - Get container logs")
        print("  - GET /images - List all Docker images")
        
    except Exception as e:
        print(f"An error occurred during the enhancement: {str(e)}")
    finally:
        ssh_client.close()
        print("SSH connection closed.")

if __name__ == "__main__":
    main()