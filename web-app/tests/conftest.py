"""set up import paths for tests."""

import os
import sys

WEB_APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, WEB_APP_DIR)
