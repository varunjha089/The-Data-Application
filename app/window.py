"""Open the application in its own window: Chrome / Edge / Brave / Chromium in 'app mode' (no tabs, no address bar) when installed,
otherwise the default browser."""
import os
import shutil
import subprocess
import sys
import webbrowser


def _candidates():
    if sys.platform == "darwin":
        base = "/Applications/%s.app/Contents/MacOS/%s"
        for n in ("Google Chrome", "Microsoft Edge", "Brave Browser", "Chromium"):
            yield base % (n, n)
    elif os.name == "nt":
        roots = [os.environ.get(k) for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
        for r in filter(None, roots):
            for rel in (r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe", r"BraveSoftware\Brave-Browser\Application\brave.exe"):
                yield os.path.join(r, rel)
    else:
        for n in ("google-chrome", "google-chrome-stable", "microsoft-edge", "brave-browser", "chromium", "chromium-browser"):
            p = shutil.which(n)
            if p:
                yield p


def screen_size():
    """(width, height) of the main screen in points, or None when it cannot be found (standard library only)"""
    try:
        if sys.platform == "darwin":
            out = subprocess.run(["osascript", "-e", 'tell application "Finder" to get bounds of window of desktop'], capture_output=True, text=True, timeout=5).stdout
            x0, y0, x1, y1 = [int(v) for v in out.replace(" ", "").split(",")]
            return x1 - x0, y1 - y0
        if os.name == "nt":
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
            return ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        size = root.winfo_screenwidth(), root.winfo_screenheight()
        root.destroy()
        return size
    except Exception:
        return None


def window_geometry():
    """size and position that fit the screen: room is left for the menu bar and the Dock / task bar, so that the whole window stays visible"""
    w, h = 1180, 860
    scr = screen_size()
    if scr:
        w, h = min(w, scr[0] - 80), min(h, scr[1] - 170)
    return max(w, 700), max(h, 480)


def open_window(url):
    """returns a short text saying how it was opened"""
    for exe in _candidates():
        if os.path.exists(exe):
            try:
                w, h = window_geometry()
                subprocess.Popen([exe, "--app=" + url, f"--window-size={w},{h}", "--window-position=40,30", "--no-first-run", "--no-default-browser-check"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return "app window (" + os.path.basename(exe) + ")"
            except OSError:
                continue
    webbrowser.open(url)
    return "default browser"
