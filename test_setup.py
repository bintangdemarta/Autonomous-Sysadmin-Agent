import json  
  
def test_config():  
    try:  
        with open('config/commands.json', 'r', encoding='utf-8') as f:  
            commands = json.load(f)  
        print(f"Config loaded successfully with {len(commands)} categories:")  
        for category in commands.keys():  
            print(f"  - {category}")  
        return True  
    except Exception as e:  
        print(f"Config loading failed: {e}")  
        return False  
  
def test_dependencies():
    deps = ['paramiko', 'colorama', 'dotenv']
    for dep in deps:
        try:
            if dep == 'dotenv':
                __import__('dotenv')
            else:
                __import__(dep)
            print(f"{dep} imported successfully")
        except ImportError as e:
            print(f"{dep} import failed: {e}")
            return False
    return True
  
if __name__ == "__main__":  
    print("Testing Nexus-CLI setup...")  
    print("1. Testing configuration:")  
    config_ok = test_config()  
    print("2. Testing dependencies:")  
    deps_ok = test_dependencies()  
    print(f"Result: {'PASS' if config_ok and deps_ok else 'FAIL'}") 
