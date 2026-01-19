from flask import Flask, render_template, request, jsonify
import json
import os
import time
import paramiko

app = Flask(__name__)

# Global variable to store command history
command_history = []

def execute_ssh_command_via_paramiko(host, user, password, command):
    """Execute a command via SSH using Paramiko"""
    try:
        # Create SSH client
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to the server
        ssh_client.connect(hostname=host, username=user, password=password)

        # Execute the command
        stdin, stdout, stderr = ssh_client.exec_command(command)
        
        # Get the output
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        # Close the connection
        ssh_client.close()

        return output, error
    except Exception as e:
        return "", str(e)

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        return render_template('index.html')
    except:
        return "<h1>Nexus-CLI Web Interface</h1><p>Available endpoints: /execute, /containers, /images, /history</p>"

@app.route('/execute', methods=['POST'])
def execute_command():
    """Execute a command via Nexus-CLI"""
    try:
        user_input = request.json.get('command', '')

        if not user_input.strip():
            return jsonify({'error': 'Command cannot be empty'}), 400

        # Load commands from config
        try:
            with open('config/commands.json', 'r', encoding='utf-8') as f:
                commands = json.load(f)
        except:
            return jsonify({'error': 'Error: Could not load command configuration'}), 500

        # Parse the command
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
            host = os.getenv('PROXMOX_HOST', '100.124.247.81')
            user = os.getenv('PROXMOX_USER', 'bintangdmrt')
            password = os.getenv('PROXMOX_PASSWORD', 'SecurePass2026!')

            output, error = execute_ssh_command_via_paramiko(host, user, password, matched_command)

            # Return the result
            if error:
                result = {
                    'success': False,
                    'output': f"Command: {matched_command}\nDescription: {description}\n\nError: {error}",
                    'parsed_command': matched_command
                }
            else:
                result = {
                    'success': True,
                    'output': f"Command: {matched_command}\nDescription: {description}\n\n{output}",
                    'parsed_command': matched_command
                }
        else:
            result = {
                'success': False,
                'output': f"Command '{user_input}' not recognized. Try commands like 'cek ram', 'cek disk', 'cek uptime', etc.",
                'parsed_command': None
            }

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

@app.route('/containers')
def list_containers():
    """Get list of Docker containers"""
    try:
        # Load SSH credentials
        host = os.getenv('PROXMOX_HOST', '100.124.247.81')
        user = os.getenv('PROXMOX_USER', 'bintangdmrt')
        password = os.getenv('PROXMOX_PASSWORD', 'SecurePass2026!')

        # Execute Docker command to list containers
        output, error = execute_ssh_command_via_paramiko(host, user, password, 'docker ps -a --format "{{.ID}}\\t{{.Names}}\\t{{.Status}}\\t{{.Ports}}"')

        if error:
            return jsonify({'error': f'Docker command failed: {error}'}), 500
        
        # Parse the output
        containers = []
        lines = output.strip().split('\\n')[1:]  # Skip header
        for line in lines:
            if line.strip():
                parts = line.split('\\t')
                if len(parts) >= 4:
                    containers.append({
                        'id': parts[0][:12],  # Short ID
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
        if action not in ['start', 'stop', 'restart', 'rm', 'logs']:
            return jsonify({'error': f'Invalid action: {action}. Valid actions: start, stop, restart, rm, logs'}), 400

        # Load SSH credentials
        host = os.getenv('PROXMOX_HOST', '100.124.247.81')
        user = os.getenv('PROXMOX_USER', 'bintangdmrt')
        password = os.getenv('PROXMOX_PASSWORD', 'SecurePass2026!')

        # Execute Docker command based on action
        if action == 'logs':
            command = f'docker logs --tail 50 {container_id}'
        elif action == 'rm':
            command = f'docker rm -f {container_id}'  # Force remove
        else:
            command = f'docker {action} {container_id}'
        
        output, error = execute_ssh_command_via_paramiko(host, user, password, command)

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

        # Execute Docker command to list images
        output, error = execute_ssh_command_via_paramiko(host, user, password, 'docker images --format "{{.ID}}\\t{{.Repository}}\\t{{.Tag}}\\t{{.Size}}"')

        if error:
            return jsonify({'error': f'Docker command failed: {error}'}), 500
        
        # Parse the output
        images = []
        lines = output.strip().split('\\n')[1:]  # Skip header
        for line in lines:
            if line.strip():
                parts = line.split('\\t')
                if len(parts) >= 4:
                    images.append({
                        'id': parts[0][:12],  # Short ID
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