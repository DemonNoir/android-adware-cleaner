#!/usr/bin/env python3
"""Android Adware & Malware Removal Tool for Mobile Repair Shops.

Entry point for launching the desktop application.
"""

import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.app import launch_app

if __name__ == "__main__":
    launch_app()
