"""Entry point for tello_vggt CLI.

This allows running the package as:
    python -m tello_vggt [command] [options]
    tello-vggt [command] [options]  (after pip install)
"""

from tello_vggt.cli.main import app

if __name__ == "__main__":
    app()
