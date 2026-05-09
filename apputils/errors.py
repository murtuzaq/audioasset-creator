import os
import sys
import threading
import traceback
import datetime
import tkinter as tk

_log_path: str | None = None
_lock = threading.Lock()


def setup(log_path: str) -> None:
    global _log_path
    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
    _log_path = log_path


def log(exc: BaseException, context: str = "") -> str:
    path = _log_path or "app.err"
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"[{timestamp}]" + (f"  {context}" if context else "")
    block = f"\n{'=' * 60}\n{header}\n{tb}"
    with _lock:
        with open(path, "a", encoding="utf-8") as f:
            f.write(block)
    return path


def show(parent: tk.Widget, exc: BaseException, context: str = "") -> None:
    log_path = log(exc, context)
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    _ErrorDialog(parent, tb, log_path)


def install_hook(root_getter) -> None:
    original = sys.excepthook

    def _hook(exc_type, exc_value, exc_tb):
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        log_path = log(exc_value, "unhandled exception")
        root = root_getter()
        if root:
            _ErrorDialog(root, tb, log_path)
        else:
            original(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook


class _ErrorDialog(tk.Toplevel):
    def __init__(self, parent: tk.Widget, tb_text: str, log_path: str):
        super().__init__(parent)
        self.title("Error")
        self.geometry("640x420")
        self.resizable(True, True)
        self.grab_set()
        self._tb = tb_text
        self._build_ui(tb_text, log_path)

    def _build_ui(self, tb_text: str, log_path: str):
        tk.Label(self, text="An error occurred:", anchor="w").pack(
            fill="x", padx=12, pady=(12, 4)
        )

        text_frame = tk.Frame(self)
        text_frame.pack(fill="both", expand=True, padx=12)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")

        self._text = tk.Text(
            text_frame,
            wrap="word",
            yscrollcommand=scrollbar.set,
            font=("Courier", 9),
            bg="#1e1e1e",
            fg="#f1f1f1",
            insertbackground="#f1f1f1",
        )
        self._text.pack(fill="both", expand=True)
        self._text.insert("1.0", tb_text)
        self._text.bind("<Key>", self._readonly_key)
        scrollbar.config(command=self._text.yview)

        tk.Label(self, text=f"Logged to: {log_path}", fg="gray", anchor="w").pack(
            fill="x", padx=12, pady=(4, 0)
        )

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=8)
        tk.Button(btn_frame, text="Copy to Clipboard", command=self._copy).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Close", command=self.destroy).pack(side="left", padx=4)

    def _readonly_key(self, event):
        if event.state & 0x4 and event.keysym.lower() in ("c", "a"):
            return  # allow Ctrl+C / Ctrl+A
        return "break"

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self._tb)
