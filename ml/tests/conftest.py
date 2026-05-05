"""fix import paths for tests."""

import os
import sys

ML_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ML_DIR)
