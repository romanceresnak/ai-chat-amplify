#!/usr/bin/env python3
"""
Build Lambda Layer for ScribbeAI Orchestrator
This script creates a Lambda layer with all required dependencies
"""

import os
import sys
import subprocess
import shutil
import zipfile
from pathlib import Path

def create_lambda_layer():
    """Create Lambda layer with Python dependencies"""
    
    # Paths
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent.parent.parent
    requirements_file = project_root / "application" / "backend" / "orchestrator" / "requirements.txt"
    layer_dir = current_dir / "layers" / "python"
    output_zip = current_dir / "python-deps-layer.zip"
    
    print(f"Building Lambda layer...")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Script location: {Path(__file__).parent}")
    print(f"Project root: {project_root}")
    print(f"Requirements file: {requirements_file}")
    print(f"Layer directory: {layer_dir}")
    print(f"Output zip: {output_zip}")
    
    # Check if requirements file exists
    if not requirements_file.exists():
        print(f"Error: Requirements file not found at {requirements_file}")
        # Create a minimal requirements file
        requirements_content = """boto3==1.28.62
langchain==0.1.0
python-pptx==0.6.23
XlsxWriter==3.1.9
pillow==10.1.0
lxml==4.9.3"""
        
        # Create directories if they don't exist
        requirements_file.parent.mkdir(parents=True, exist_ok=True)
        requirements_file.write_text(requirements_content)
        print("Created requirements.txt with default dependencies")
    
    # Clean up existing layer directory
    if layer_dir.exists():
        shutil.rmtree(layer_dir.parent)
    
    # Create layer directory
    layer_dir.mkdir(parents=True)
    
    # Try to find pip
    pip_cmd = None
    for cmd in ["pip3", "python3 -m pip", "pip", "python -m pip"]:
        try:
            subprocess.run(cmd.split() + ["--version"], 
                         capture_output=True, check=True)
            pip_cmd = cmd
            break
        except:
            continue
    
    if not pip_cmd:
        print("Error: pip not found. Please install Python and pip.")
        print("On macOS: brew install python3")
        print("On Ubuntu: sudo apt-get install python3-pip")
        sys.exit(1)
    
    print(f"Using pip command: {pip_cmd}")
    
    # Install dependencies - properly quote paths with spaces
    cmd = [pip_cmd] if ' ' not in pip_cmd else pip_cmd.split()
    cmd.extend([
        'install', 
        '-r', str(requirements_file),
        '-t', str(layer_dir),
        '--upgrade'
    ])
    
    print("Installing dependencies...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error installing dependencies: {result.stderr}")
            # Try without --upgrade option
            cmd_simple = [pip_cmd] if ' ' not in pip_cmd else pip_cmd.split()
            cmd_simple.extend([
                'install', 
                '-r', str(requirements_file),
                '-t', str(layer_dir)
            ])
            print("Trying simplified install command...")
            result = subprocess.run(cmd_simple, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Error: {result.stderr}")
                sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    print("Dependencies installed successfully")
    
    # Create zip file
    print(f"Creating zip file: {output_zip}")
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(layer_dir.parent):
            for file in files:
                file_path = Path(root) / file
                arcname = str(file_path.relative_to(layer_dir.parent))
                zipf.write(file_path, arcname)
    
    print(f"Lambda layer created: {output_zip}")
    print(f"Size: {output_zip.stat().st_size / 1024 / 1024:.2f} MB")
    
    # Clean up
    shutil.rmtree(layer_dir.parent)
    
    return str(output_zip)

if __name__ == "__main__":
    create_lambda_layer()