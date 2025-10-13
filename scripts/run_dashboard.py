#!/usr/bin/env python3
"""
Script to run the MCP Operations Dashboard
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import and run dashboard
from servers.dashboard_server import main

if __name__ == "__main__":
    main()
