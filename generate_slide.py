#!/usr/bin/env python3
"""
Simple slide generator - universal endpoint for any prompt
"""

import os
import sys
import subprocess

def main():
    """Main function to generate slide from prompt"""
    
    # Get prompt from arguments or stdin
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        print("Zadaj prompt pre generovanie slide:")
        prompt = input().strip()
    
    if not prompt:
        print("❌ Musíš zadať prompt!")
        return
    
    print(f"Generujem slide pre: {prompt}")
    
    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(script_dir, "venv", "bin", "python")
    universal_script = os.path.join(script_dir, "universal_slide_generator.py")
    
    # Check if venv exists
    if not os.path.exists(venv_python):
        print("❌ Virtual environment neexistuje. Spusti najprv:")
        print("python3 -m venv venv")
        print("source venv/bin/activate") 
        print("pip install python-pptx boto3")
        return
    
    # Run the universal generator
    try:
        result = subprocess.run(
            [venv_python, universal_script, prompt],
            cwd=script_dir,
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.stderr:
            print("Varovania:", result.stderr)
            
    except Exception as e:
        print(f"❌ Chyba pri spustení: {e}")

if __name__ == "__main__":
    main()