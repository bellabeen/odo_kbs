#!/usr/bin/env python3
"""CI Quick-run script: runs compileall checks and all unit/integration tests.

Usage: python run_tests.py
"""
import sys
import compileall
import unittest
from pathlib import Path

# Repo root
ROOT = Path(__file__).resolve().parent

def run_compile() -> bool:
    print("--- 1. Compiling Python files ---")
    res = compileall.compile_dir(ROOT, quiet=1)
    if not res:
        print("FAIL: Compilation error detected.")
        return False
    print("OK: Compilation success.")
    return True

def run_tests() -> bool:
    print("\n--- 2. Running Test Suite ---")
    # Discover tests inside kbs_storage_yai
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(ROOT), pattern="test_*.py")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()

def main() -> int:
    success = run_compile()
    if not success:
        return 1
        
    success = run_tests()
    if not success:
        print("\nFAIL: One or more tests failed.")
        return 1
        
