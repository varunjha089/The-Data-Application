"""Windows (and anywhere): double-click to open The Data Application as a window, without a console window.
.pyw files are started by pythonw, which shows no console. Errors go to app.log in the application's settings folder and a message box."""
import os
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.chdir(HERE)
sys.path.insert(0, str(HERE))
try:
    if sys.version_info < (3, 9):
        raise RuntimeError("Python 3.9 or newer is needed (this is %d.%d)." % sys.version_info[:2])
    from app.cli import main
    sys.exit(main(["gui"]))
except SystemExit:
    raise
except Exception:
    text = traceback.format_exc()
    try:
        from app.paths import APP_LOG                      # the application's own settings folder
        APP_LOG.parent.mkdir(parents=True, exist_ok=True)
        APP_LOG.write_text(text, encoding="utf-8")
    except Exception:
        (HERE / "app_error.log").write_text(text, encoding="utf-8")
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, "The Data Application could not start.\n\n" + text[-600:], "The Data Application", 0x10)
    except Exception:
        pass
