"""
VCI — Python wrapper for the Luminova Version Control Interface.

Provides a CLI entry point and a programmatic API for running phpvci.sh
from Python code or build pipelines.

Typical usage
-------------
Command line (after pip install):
    phpvci package --install=3.8.9
    phpvci package --list
    phpvci self --update

Programmatic:
    from phpvci import runner
    exit_code = runner.run(["package", "--install=3.8.9", "--runtime=user"])
"""

__version__ = "1.3.3"
__author__ = "Luminova"
__license__ = "MIT"

__all__ = ["runner", "cli"]
