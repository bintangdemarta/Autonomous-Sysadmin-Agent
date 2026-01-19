#!/usr/bin/env python3
"""
Instructions for completing Cloudflare Tunnel setup
"""

import os
from dotenv import load_dotenv

def main():
    """
    Display instructions for completing Cloudflare Tunnel setup
    """
    print("="*60)
    print("CLOUDFLARE TUNNEL SETUP INSTRUCTIONS")
    print("="*60)
    
    print("\nCloudflared has been successfully installed on your server!")
    print("Version:", "2025.11.1")
    
    print("\nThe automated setup encountered an authentication requirement.")
    print("Cloudflare Tunnel requires manual authentication to your Cloudflare account.")
    
    print("\nTo complete the setup, please follow these steps:")
    
    print("\n1. On your local machine (not the server), install Cloudflare CLI:")
    print("   Download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/")
    
    print("\n2. Authenticate with Cloudflare on your local machine:")
    print("   cloudflared tunnel login")
    
    print("\n3. Once authenticated locally, copy the certificate file to your server:")
    print("   The certificate is typically located at ~/.cloudflared/cert.pem on your local machine")
    print("   Copy it to the server at /home/bintangdmrt/.cloudflared/cert.pem")
    
    print("\n4. OR alternatively, run the authentication directly on the server:")
    print("   a) SSH into your server:")
    print("      ssh bintangdmrt@100.124.247.81")
    print("   b) Run the login command (this will open a browser on the server, which may require X11 forwarding):")
    print("      cloudflared tunnel login")
    
    print("\n5. After authentication, create a tunnel with a specific name:")
    print("   cloudflared tunnel create nexus-cli")
    
    print("\n6. Route the tunnel to your application:")
    print("   cloudflared tunnel route dns nexus-cli yourdomain.com")
    
    print("\n7. Create the configuration file on the server:")
    print("   nano ~/.cloudflared/config.yml")
    print("   Add the following content:")
    print("""ingress:
  - hostname: yourdomain.com
    service: http://localhost:5000
  - service: http_status:404""")
    
    print("\n8. Start the tunnel as a service:")
    print("   sudo systemctl enable cloudflared-tunnel.service")
    print("   sudo systemctl start cloudflared-tunnel.service")
    
    print("\n9. Check the status:")
    print("   sudo systemctl status cloudflared-tunnel.service")
    
    print("\nOnce completed, your application will be accessible via HTTPS at your chosen domain,")
    print("with traffic securely tunneled through Cloudflare to your server on port 5000.")
    
    print("\nYour web application is currently running and accessible at:")
    print("  http://100.124.247.81:5000")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()