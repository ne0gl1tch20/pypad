"""Expose a simple entry point that delegates startup into the packaged application modules.

This module belongs to the application codebase. It helps explain how `` is structured and where this file fits into the runtime workflow.
"""

from pypad.app import main

if __name__ == "__main__":
    main()
