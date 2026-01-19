from flask import Flask, render_template, request, jsonify
import subprocess
import json
import os
from threading import Thread
import time
import paramiko

app = Flask(__name__)

# Global variable to store command history
command_history = []

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard with system info"""
    return render_template('index.html')

@app.route('/commands')
def commands():
    """Page to manage commands"""
    return render_template('commands.html')

@app.route('/execute', methods=['POST'])
def execute_command():
    """Execute a command via Nexus-CLI"""
    try:
        user_input = request.json.get('command', '')

        if not user_input.strip():
            return jsonify({'error': 'Command cannot be empty'}), 400

        # Execute the command using Nexus-CLI via SSH
        result = execute_ssh_command(user_input)

        # Add to command history
        command_entry = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'input': user_input,
            'output': result['output'],
            'success': result['success']
        }
        command_history.insert(0, command_entry)

        # Keep only the last 50 commands
        if len(command_history) > 50:
            command_history[:] = command_history[:50]

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def execute_ssh_command(user_input):
    """Execute Nexus-CLI command via SSH"""
    # Load commands from config
    try:
        with open('config/commands.json', 'r', encoding='utf-8') as f:
            commands = json.load(f)
    except:
        return {
            'success': False,
            'output': 'Error: Could not load command configuration',
            'parsed_command': None
        }

    # Parse the command (simplified version of what main.py does)
    user_input_lower = user_input.lower().strip()
    matched_command = None
    description = ""

    # Search through all command categories
    for category, cmds in commands.items():
        for cmd in cmds:
            # Check for keyword matches
            if 'keywords' in cmd:
                for keyword in cmd['keywords']:
                    if keyword in user_input_lower:
                        matched_command = cmd['command']
                        description = cmd.get('description', '')
                        break
            # Check for pattern matches (regex)
            if 'pattern' in cmd and not matched_command:
                import re
                pattern = cmd['pattern']
                match = re.search(pattern, user_input_lower)
                if match:
                    # Format command with captured groups
                    matched_command = cmd['command'].format(*match.groups())
                    description = cmd.get('description', '')

    if matched_command:
        # Execute the command via SSH
        try:
            # Load SSH credentials from environment or config
            import os
            from dotenv import load_dotenv
            load_dotenv()

            host = os.getenv('PROXMOX_HOST', '100.124.247.81')
            user = os.getenv('PROXMOX_USER', 'bintangdmrt')
            password = os.getenv('PROXMOX_PASSWORD', 'SecurePass2026!')

            # Create SSH client
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Connect to the server
            ssh_client.connect(hostname=host, username=user, password=password)

            # Execute the command
            stdin, stdout, stderr = ssh_client.exec_command(matched_command)
            
            # Get the output
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')

            # Close the connection
            ssh_client.close()

            # Return the result
            if error:
                return {
                    'success': False,
                    'output': f"Command: {matched_command}\nDescription: {description}\n\nError: {error}",
                    'parsed_command': matched_command
                }
            else:
                return {
                    'success': True,
                    'output': f"Command: {matched_command}\nDescription: {description}\n\n{output}",
                    'parsed_command': matched_command
                }

        except Exception as e:
            return {
                'success': False,
                'output': f"Failed to execute command via SSH: {str(e)}",
                'parsed_command': matched_command
            }
    else:
        return {
            'success': False,
            'output': f"Command '{user_input}' not recognized. Try commands like 'cek ram', 'cek disk', 'cek uptime', etc.",
            'parsed_command': None
        }

@app.route('/containers')
def list_containers():
    """Get list of Docker containers"""
    try:
        # Load SSH credentials
        host = os.getenv('PROXMOX_HOST', '100.124.247.81')
        user = os.getenv('PROXMOX_USER', 'bintangdmrt')
        password = os.getenv('PROXMOX_PASSWORD', 'SecurePass2026!')

        # Create SSH client
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to the server
        ssh_client.connect(hostname=host, username=user, password=password)

        # Execute Docker command to list containers
        stdin, stdout, stderr = ssh_client.exec_command('docker ps -a --format "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"')
        
        # Get the output
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        # Close the connection
        ssh_client.close()

        if error:
            return jsonify({'error': f'Docker command failed: {error}'}), 500
        
        # Parse the output
        containers = []
        lines = output.strip().split('\n')[1:]  # Skip header
        for line in lines:
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 4:
                    containers.append({
                        'id': parts[0],
                        'name': parts[1],
                        'status': parts[2],
                        'ports': parts[3]
                    })
        
        return jsonify(containers)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/container/<container_id>/<action>', methods=['POST'])
def container_action(container_id, action):
    """Perform an action on a Docker container (start, stop, restart, remove)"""
    try:
        # Validate action
        if action not in ['start', 'stop', 'restart', 'remove', 'logs']:
            return jsonify({'error': f'Invalid action: {action}'}), 400

        # Load SSH credentials
        host = os.getenv('PROXMOX_HOST', '100.124.247.81')
        user = os.getenv('PROXMOX_USER', 'bintangdmrt')
        password = os.getenv('PROXMOX_PASSWORD', 'SecurePass2026!')

        # Create SSH client
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to the server
        ssh_client.connect(hostname=host, username=user, password=password)

        # Execute Docker command based on action
        if action == 'logs':
            stdin, stdout, stderr = ssh_client.exec_command(f'docker logs --tail 50 {container_id}')
        else:
            stdin, stdout, stderr = ssh_client.exec_command(f'docker {action} {container_id}')
        
        # Get the output
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        # Close the connection
        ssh_client.close()

        if error:
            return jsonify({'error': f'Docker {action} command failed: {error}'}), 500
        
        return jsonify({
            'success': True,
            'message': f'Container {container_id} {action}ed successfully',
            'output': output
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/images')
def list_images():
    """Get list of Docker images"""
    try:
        # Load SSH credentials
        host = os.getenv('PROXMOX_HOST', '100.124.247.81')
        user = os.getenv('PROXMOX_USER', 'bintangdmrt')
        password = os.getenv('PROXMOX_PASSWORD', 'SecurePass2026!')

        # Create SSH client
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to the server
        ssh_client.connect(hostname=host, username=user, password=password)

        # Execute Docker command to list images
        stdin, stdout, stderr = ssh_client.exec_command('docker images --format "{{.ID}}\t{{.Repository}}\t{{.Tag}}\t{{.Size}}"')
        
        # Get the output
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        # Close the connection
        ssh_client.close()

        if error:
            return jsonify({'error': f'Docker command failed: {error}'}), 500
        
        # Parse the output
        images = []
        lines = output.strip().split('\n')[1:]  # Skip header
        for line in lines:
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 4:
                    images.append({
                        'id': parts[0],
                        'repository': parts[1],
                        'tag': parts[2],
                        'size': parts[3]
                    })
        
        return jsonify(images)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/history')
def get_history():
    """Get command execution history"""
    return jsonify(command_history)

@app.route('/history/clear', methods=['POST'])
def clear_history():
    """Clear command execution history"""
    global command_history
    command_history = []
    return jsonify({'success': True, 'message': 'History cleared successfully'})

@app.route('/config', methods=['GET', 'POST'])
def manage_config():
    """Manage command configuration"""
    if request.method == 'POST':
        try:
            new_config = request.json
            with open('config/commands.json', 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=2, ensure_ascii=False)
            return jsonify({'success': True, 'message': 'Configuration updated successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # GET request - return current config
    try:
        with open('config/commands.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        return jsonify(config)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)