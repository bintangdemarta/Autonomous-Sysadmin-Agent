#!/usr/bin/env python3
# Test script for Nexus-CLI functionality

import json
import re

def test_command_parsing():
    """Test the command parsing functionality without connecting to SSH"""
    # Load commands from config
    with open('config/commands.json', 'r', encoding='utf-8') as f:
        commands = json.load(f)

    def parse_command(user_input, commands):
        user_input_lower = user_input.lower().strip()
        
        # Search through all command categories
        for category, cmds in commands.items():
            for cmd in cmds:
                # Check for keyword matches
                if 'keywords' in cmd:
                    for keyword in cmd['keywords']:
                        if keyword in user_input_lower:
                            return cmd['command'], cmd.get('is_dangerous', False), cmd.get('description', '')
                
                # Check for pattern matches (regex)
                if 'pattern' in cmd:
                    pattern = cmd['pattern']
                    match = re.search(pattern, user_input_lower)
                    if match:
                        # Format command with captured groups
                        command = cmd['command'].format(*match.groups())
                        return command, cmd.get('is_dangerous', False), cmd.get('description', '')
        
        # If no match found, return None
        return None, False, ""

    # Test the parsing
    test_inputs = [
        'cek ram',
        'check memory', 
        'hidupkan vm 102',
        'matikan vm 103',
        'server uptime'
    ]

    print('Command parsing test:')
    for inp in test_inputs:
        command, is_dangerous, description = parse_command(inp, commands)
        print(f'Input: {inp} -> Command: {command}, Dangerous: {is_dangerous}, Desc: {description}')

if __name__ == "__main__":
    test_command_parsing()