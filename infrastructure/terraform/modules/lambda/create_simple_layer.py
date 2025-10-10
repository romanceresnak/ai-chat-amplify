#!/usr/bin/env python3
"""
Create a simple Lambda layer with basic dependencies for ScribbeAI
"""

import subprocess
import sys
import zipfile
import os
from pathlib import Path

def create_simple_layer():
    """Create a simple Lambda layer"""
    
    current_dir = Path(__file__).parent
    layer_dir = current_dir / "temp_layer" / "python"
    output_zip = current_dir / "python-deps-layer.zip"
    
    print("Creating simple Lambda layer...")
    
    # Clean up
    if layer_dir.exists():
        import shutil
        shutil.rmtree(layer_dir.parent)
    
    # Create directory
    layer_dir.mkdir(parents=True)
    
    # Simple requirements that should work
    simple_deps = [
        "boto3>=1.28.0",
        "python-pptx>=0.6.21", 
        "requests>=2.31.0",
        "Pillow>=10.0.0"
    ]
    
    pip_cmd = "pip3"
    
    # Install each dependency separately
    for dep in simple_deps:
        print(f"Installing {dep}...")
        cmd = [pip_cmd, "install", dep, "-t", str(layer_dir), "--no-deps"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Warning: Failed to install {dep}: {result.stderr}")
                # Try without --no-deps
                cmd = [pip_cmd, "install", dep, "-t", str(layer_dir)]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"Error: Still failed to install {dep}")
                    continue
        except Exception as e:
            print(f"Error installing {dep}: {e}")
            continue
    
    # Install core dependencies manually
    basic_deps = ["boto3", "requests"]
    for dep in basic_deps:
        print(f"Installing {dep} with dependencies...")
        cmd = [pip_cmd, "install", dep, "-t", str(layer_dir)]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except:
            print(f"Warning: Failed to install {dep}")
    
    # Create zip file
    print(f"Creating zip file: {output_zip}")
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(layer_dir.parent):
            for file in files:
                file_path = Path(root) / file
                arcname = str(file_path.relative_to(layer_dir.parent))
                zipf.write(file_path, arcname)
    
    # Clean up
    import shutil
    shutil.rmtree(layer_dir.parent)
    
    print(f"Lambda layer created: {output_zip}")
    return str(output_zip)

if __name__ == "__main__":
    create_simple_layer()