from flask import Flask, render_template, request, jsonify
import subprocess
import json
import os
from threading import Thread
import time

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
        
        # Execute the command using Nexus-CLI
        # Note: In a real implementation, this would connect to an actual SSH server
        # For demo purposes, we'll simulate the response
        result = simulate_nexus_cli_command(user_input)
        
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

def simulate_nexus_cli_command(user_input):
    """Simulate Nexus-CLI command execution"""
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
        # Simulate command execution
        simulated_output = f"Simulated execution of: {matched_command}\nDescription: {description}\n\n"
        if "ram" in user_input_lower or "memory" in user_input_lower:
            simulated_output += "              total        used        free      shared  buff/cache   available\nMem:           7.7G        1.2G        5.2G        232M        1.3G        6.1G\nSwap:            0B          0B          0B"
        elif "disk" in user_input_lower or "storage" in user_input_lower:
            simulated_output += "Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1        20G  5.2G   14G  28% /\n/dev/sda2       100G   12G   84G  13% /home"
        elif "uptime" in user_input_lower:
            simulated_output += " 11:30:42 up 5 days,  3:21,  2 users,  load average: 0.12, 0.08, 0.05"
        else:
            simulated_output += f"Command '{matched_command}' would be executed on the target server."
        
        return {
            'success': True,
            'output': simulated_output,
            'parsed_command': matched_command
        }
    else:
        return {
            'success': False,
            'output': f"Command '{user_input}' not recognized. Try commands like 'cek ram', 'cek disk', 'cek uptime', etc.",
            'parsed_command': None
        }

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
    app.run(debug=False, host='127.0.0.1', port=5000)