#!/usr/bin/env python3
"""Shim for backwards compatibility. Shell scripts call 'python cli-tool.py'."""
from spec_validator import main
if __name__ == "__main__":
    main()
