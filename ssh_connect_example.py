"""
Example script to connect to Ubuntu-Server via SSH using credentials from .env file
"""
import paramiko
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def connect_to_server():
    """
    Connect to Ubuntu-Server via SSH using credentials from environment variables
    """
    # Get credentials from environment variables
    host = os.getenv('PROXMOX_HOST')
    user = os.getenv('PROXMOX_USER')
    password = os.getenv('PROXMOX_PASSWORD')

    # Validate that all credentials are present
    if not all([host, user, password]):
        raise ValueError("Missing required environment variables for Ubuntu-Server connection")

    # Create SSH client
    ssh_client = paramiko.SSHClient()

    # Automatically add the server's host key (this is insecure in production)
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the Ubuntu-Server
        ssh_client.connect(hostname=host, username=user, password=password)

        # Execute a simple command to test the connection
        stdin, stdout, stderr = ssh_client.exec_command('hostname')
        hostname = stdout.read().decode().strip()

        print(f"Successfully connected to Ubuntu-Server: {hostname}")
        print(f"Server IP: {host}")

        # Close the connection
        ssh_client.close()

        return True

    except Exception as e:
        print(f"Failed to connect to Ubuntu-Server: {str(e)}")
        return False

if __name__ == "__main__":
    connect_to_server()