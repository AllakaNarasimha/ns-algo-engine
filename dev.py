#!/usr/bin/env python3
"""
Development Setup and Runner
Single script to setup environment and run the application
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description, shell=False):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=shell, capture_output=False)
    if result.returncode != 0:
        print(f"\nError {description} failed!")
        return False
    print(f"Ok {description} completed successfully")
    return True

def setup_environment():
    """Setup virtual environment and install dependencies"""
    venv_path = Path(".venv")
    python_exe = venv_path / "Scripts" / "python.exe"
    pip_exe = venv_path / "Scripts" / "pip.exe"
    
    # Create virtual environment
    if not venv_path.exists():
        if not run_command([sys.executable, "-m", "venv", ".venv"], "Creating virtual environment"):
            return False
    else:
        print("\nOk Virtual environment already exists")
    
    # Upgrade pip
    if not run_command([str(python_exe), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], 
                       "Upgrading pip", shell=False):
        return False
    
    # Install dependencies
    if not run_command([str(pip_exe), "install", "-r", "requirements.txt"], 
                       "Installing dependencies"):
        return False
    
    # Install bundled packages
    libs_dir = Path("client/libs")
    if libs_dir.exists():
        for pkg in ["nslogger-1.0.0.tar.gz", "trading_api-1.0.0.tar.gz"]:
            pkg_path = libs_dir / pkg
            if pkg_path.exists():
                run_command([str(pip_exe), "install", "--no-deps", str(pkg_path)], 
                           f"Installing {pkg}")
    
    return True

def run_application():
    """Run the option chain monitor"""
    python_exe = Path(".venv/Scripts/python.exe")
    
    if not python_exe.exists():
        print("\nError Virtual environment not found!")
        print("Running setup first...\n")
        if not setup_environment():
            sys.exit(1)
    
    print("\n" + "="*60)
    print("Starting Option Chain Monitor")
    print("="*60 + "\n")
    
    subprocess.run([str(python_exe), "option_chain_monitor_api_simple.py"])

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Development tool for Option Chain Monitor")
    parser.add_argument("command", nargs="?", default="run", 
                       choices=["setup", "run"], 
                       help="Command to execute (setup or run)")
    
    args = parser.parse_args()
    
    if args.command == "setup":
        if setup_environment():
            print("\n" + "="*60)
            print("Ok Setup Complete!")
            print("="*60)
            print("\nTo run the application:")
            print("  python dev.py run")
        else:
            sys.exit(1)
    # else:  # run
    #     run_application()
