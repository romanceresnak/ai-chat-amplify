"""
Environment variable loader for development
Loads variables from .env file when running locally
"""
import os
import sys
from pathlib import Path

def load_env_file():
    """Load environment variables from .env file"""
    # Find .env file in project root
    current_dir = Path(__file__).resolve()
    
    # Go up directories until we find .env or reach root
    for parent in current_dir.parents:
        env_file = parent / '.env'
        if env_file.exists():
            print(f"Loading environment from: {env_file}")
            load_env_from_file(env_file)
            return
    
    print("No .env file found, using system environment variables")

def load_env_from_file(env_file_path):
    """Load environment variables from file"""
    try:
        with open(env_file_path, 'r') as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Split on first = sign
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # Set environment variable only if not already set
                    if key not in os.environ:
                        os.environ[key] = value
                        print(f"Loaded: {key}={'*' * len(value) if 'key' in key.lower() or 'secret' in key.lower() else value}")
                else:
                    print(f"Warning: Invalid line {line_num} in .env file: {line}")
                    
    except Exception as e:
        print(f"Error loading .env file: {e}")

# Auto-load when imported
if __name__ != "__main__":
    load_env_file()