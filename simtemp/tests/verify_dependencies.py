#!/usr/bin/env python3
"""
Dependency verification script for simtemp test suite.
Verifies that all required Python packages are available.
"""

import sys

def check_dependency(package_name, import_name=None):
    """Check if a Python package is available"""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        print(f"✅ {package_name}: Available")
        return True
    except ImportError:
        print(f"❌ {package_name}: Missing")
        return False

def main():
    """Verify all required dependencies"""
    print("=== Simtemp Test Dependencies Verification ===")
    
    dependencies = [
        ("PyYAML", "yaml"),
        ("requests", "requests"),
        ("pytest", "pytest"),
    ]
    
    all_available = True
    for package_name, import_name in dependencies:
        if not check_dependency(package_name, import_name):
            all_available = False
    
    print("\n=== Summary ===")
    if all_available:
        print("✅ All dependencies are available!")
        return 0
    else:
        print("❌ Some dependencies are missing.")
        print("\nTo install missing dependencies:")
        print("\n# Recommended for CI/Docker environments:")
        print("sudo apt-get update")
        print("sudo apt-get install -y python3-yaml python3-requests python3-pytest")
        print("\n# Alternative (pip):")
        print("pip install -r tests/requirements.txt")
        print("pip install pyyaml requests pytest")
        return 1

if __name__ == "__main__":
    sys.exit(main())