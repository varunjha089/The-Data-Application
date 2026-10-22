#!/usr/bin/env python3
"""The Data Application: launcher. Uses the Python standard library only, so any Python 3.9+ can start it;
the real work (cleaning, later the plots) runs in a virtual environment that the application sets up for you.

    python3 the_data_app.py            open the application window
    python3 the_data_app.py menu       the same things as a text menu in the terminal
    python3 the_data_app.py status     what is set up
    python3 the_data_app.py env --create | --venv PATH      create or point to the venv
    python3 the_data_app.py data [FILE]                     choose the main data (a copy is made inside this folder)
    python3 the_data_app.py clean                           clean the main data
"""
import sys

if sys.version_info < (3, 9):
    sys.exit("The Data Application needs Python 3.9 or newer (this is %d.%d). Get a newer one from https://www.python.org/downloads/" % sys.version_info[:2])

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
