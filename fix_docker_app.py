#!/usr/bin/env python3
"""
Script to fix and deploy the Docker-focused web application
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

def upload_docker_focused_app(ssh_client):
    """
    Upload the Docker-focused web application
    """
    print("Uploading Docker-focused web application...")
    
    # Use SFTP to upload the Docker-focused app.py file
    sftp = ssh_client.open_sftp()
    
    # Upload the Docker-focused app.py file from our local file
    local_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'docker_focused_app.py')
    remote_app_path = '/home/bintangdmrt/nexus-cli/web/app.py'
    
    print(f"Uploading {local_app_path} to {remote_app_path}...")
    sftp.put(local_app_path, remote_app_path)
    
    sftp.close()
    print("Docker-focused application uploaded successfully!")

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
    time.sleep(5)
    
    # Check if the process is running
    stdin, stdout, stderr = ssh_client.exec_command('ps aux | grep "python web/app.py" | grep -v grep')
    process_output = stdout.read().decode()
    
    if process_output:
        print("Web application restarted successfully!")
        print(f"The web application should now be accessible at http://{os.getenv('PROXMOX_HOST', '100.124.247.81')}:5000")
        print("It now includes Docker/container management features.")
    else:
        print("Could not confirm that the application restarted properly.")
        # Let's check what happened
        stdin, stdout, stderr = ssh_client.exec_command('cat /home/bintangdmrt/nexus-cli/app.log | tail -10')
        log_output = stdout.read().decode()
        print("Last 10 lines of app.log:")
        print(log_output)

def test_docker_endpoints(ssh_client):
    """
    Test if Docker endpoints are working
    """
    print("\\nTesting Docker endpoints...")
    
    # Test containers endpoint
    try:
        stdin, stdout, stderr = ssh_client.exec_command('curl -s http://localhost:5000/containers')
        output = stdout.read().decode()
        print(f"Containers endpoint test result: {len(output)} characters returned")
        if '"error"' in output.lower():
            print(f"Error in containers response: {output[:200]}...")
        else:
            print("Containers endpoint appears to be working")
    except Exception as e:
        print(f"Error testing containers endpoint: {str(e)}")
    
    # Test images endpoint
    try:
        stdin, stdout, stderr = ssh_client.exec_command('curl -s http://localhost:5000/images')
        output = stdout.read().decode()
        print(f"Images endpoint test result: {len(output)} characters returned")
        if '"error"' in output.lower():
            print(f"Error in images response: {output[:200]}...")
        else:
            print("Images endpoint appears to be working")
    except Exception as e:
        print(f"Error testing images endpoint: {str(e)}")

def main():
    """
    Main function to deploy the Docker-focused web application
    """
    print("Deploying Docker-focused web application...")
    print("This will:")
    print("  1. Replace the app.py with Docker-focused version")
    print("  2. Restart the web application")
    print("  3. Test Docker endpoints")
    
    # Connect to the server
    ssh_client = connect_to_server()
    if not ssh_client:
        print("Failed to connect to the server. Exiting.")
        sys.exit(1)
    
    try:
        # Upload the Docker-focused application
        upload_docker_focused_app(ssh_client)
        
        # Restart the application to apply changes
        restart_application(ssh_client)
        
        # Test Docker endpoints
        test_docker_endpoints(ssh_client)
        
        print("\\nApplication successfully updated with Docker-focused features!")
        print("New endpoints available:")
        print("  - GET /containers - List all Docker containers")
        print("  - POST /container/<id>/start - Start a container")
        print("  - POST /container/<id>/stop - Stop a container")
        print("  - POST /container/<id>/restart - Restart a container")
        print("  - POST /container/<id>/rm - Remove a container")
        print("  - POST /container/<id>/logs - Get container logs")
        print("  - GET /images - List all Docker images")
        
    except Exception as e:
        print(f"An error occurred during the deployment: {str(e)}")
    finally:
        ssh_client.close()
        print("SSH connection closed.")

if __name__ == "__main__":
    main()