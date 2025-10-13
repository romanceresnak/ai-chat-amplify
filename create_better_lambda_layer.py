#!/usr/bin/env python3
"""
Create a better Lambda layer specifically for python-pptx with all dependencies
"""

import subprocess
import sys
import zipfile
import os
import shutil
from pathlib import Path

def create_pptx_layer():
    """Create Lambda layer optimized for python-pptx"""
    
    print("Creating optimized Lambda layer for python-pptx...")
    
    current_dir = Path(__file__).parent
    layer_dir = current_dir / "pptx_layer" / "python" / "lib" / "python3.11" / "site-packages"
    output_zip = current_dir / "python-pptx-optimized-layer.zip"
    
    # Clean up
    if (current_dir / "pptx_layer").exists():
        shutil.rmtree(current_dir / "pptx_layer")
    
    # Create directory structure
    layer_dir.mkdir(parents=True)
    
    # Install python-pptx and minimal dependencies
    print("Installing python-pptx with dependencies...")
    subprocess.run([
        sys.executable, "-m", "pip", "install",
        "--target", str(layer_dir),
        "--no-cache-dir",
        "--upgrade",
        "python-pptx==0.6.23",  # Specific stable version
        "lxml>=4.6.0",
        "Pillow>=8.0.0",
        "XlsxWriter>=3.0.0"
    ], check=True)
    
    # Remove unnecessary files to reduce size
    print("Optimizing layer size...")
    patterns_to_remove = [
        "**/*.pyc",
        "**/__pycache__",
        "**/*.pyi",
        "**/tests",
        "**/test",
        "**/*.dist-info/RECORD",
        "**/*.dist-info/WHEEL",
        "**/*.dist-info/top_level.txt"
    ]
    
    for pattern in patterns_to_remove:
        for file in layer_dir.rglob(pattern):
            if file.is_file():
                file.unlink()
            elif file.is_dir():
                shutil.rmtree(file)
    
    # Create zip
    print("Creating zip file...")
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(current_dir / "pptx_layer"):
            for file in files:
                file_path = Path(root) / file
                arcname = str(file_path.relative_to(current_dir / "pptx_layer"))
                zf.write(file_path, arcname)
    
    # Clean up
    shutil.rmtree(current_dir / "pptx_layer")
    
    size_mb = output_zip.stat().st_size / (1024 * 1024)
    print(f"✅ Lambda layer created: {output_zip}")
    print(f"   Size: {size_mb:.2f} MB")
    
    return str(output_zip)

if __name__ == "__main__":
    create_pptx_layer()