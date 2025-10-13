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
    
    # Required dependencies with all sub-dependencies
    required_deps = [
        "boto3>=1.28.0",
        "python-pptx>=0.6.21", 
        "requests>=2.31.0",
        "Pillow>=10.0.0",
        "lxml>=4.9.0",  # Required by python-pptx
        "PyPDF2>=3.0.0"  # For PDF parsing
    ]
    
    pip_cmd = "pip3"
    
    # Install all dependencies with their subdependencies
    print("Installing all dependencies with subdependencies...")
    cmd = [pip_cmd, "install"] + required_deps + ["-t", str(layer_dir)]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error installing dependencies: {result.stderr}")
            print("Trying to install individually...")
            
            # Install each dependency individually with full dependencies
            for dep in required_deps:
                print(f"Installing {dep} with all dependencies...")
                cmd = [pip_cmd, "install", dep, "-t", str(layer_dir)]
                
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        print(f"Warning: Failed to install {dep}: {result.stderr}")
                    else:
                        print(f"Successfully installed {dep}")
                except Exception as e:
                    print(f"Error installing {dep}: {e}")
        else:
            print("All dependencies installed successfully")
            
    except Exception as e:
        print(f"Error during installation: {e}")
        
    # Verify critical packages are installed
    critical_packages = ["pptx", "boto3", "requests", "PIL", "lxml"]
    for pkg in critical_packages:
        pkg_path = layer_dir / pkg
        if pkg_path.exists():
            print(f"✓ {pkg} installed")
        else:
            print(f"✗ {pkg} missing - this may cause import errors")
    
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