#!/usr/bin/env python3
"""
Test runner script for SQL RAG modular application tests
"""
import sys
import subprocess
from pathlib import Path

def run_tests(test_type: str = "all", verbose: bool = False):
    """
    Run tests with pytest
    
    Args:
        test_type: Type of tests to run ("unit", "integration", "all")
        verbose: Enable verbose output
    """
    project_root = Path(__file__).parent.parent
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add verbose flag if requested
    if verbose:
        cmd.append("-v")
    
    # Add test directory based on type
    if test_type == "unit":
        cmd.append("tests/unit/")
    elif test_type == "integration":
        cmd.append("tests/integration/")
    elif test_type == "all":
        cmd.append("tests/")
    else:
        print(f"Unknown test type: {test_type}")
        print("Valid options: unit, integration, all")
        return 1
    
    # Add coverage if available
    try:
        import coverage
        cmd.extend(["--cov=modular", "--cov-report=term-missing"])
    except ImportError:
        print("Note: Install pytest-cov for coverage reporting")
    
    print(f"Running {test_type} tests...")
    print(f"Command: {' '.join(cmd)}")
    
    # Change to project directory and run tests
    result = subprocess.run(cmd, cwd=project_root)
    return result.returncode


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run SQL RAG tests")
    parser.add_argument(
        "test_type", 
        nargs="?", 
        default="all",
        choices=["unit", "integration", "all"],
        help="Type of tests to run"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    return run_tests(args.test_type, args.verbose)


if __name__ == "__main__":
    sys.exit(main())