import tkinter as tk
from tkinter import filedialog, messagebox
from audioasset_creator import save

AUDIO_FILETYPES = [
    ("Audio files", "*.mp3 *.wav *.flac *.aac *.ogg *.m4a *.wma"),
    ("All files", "*.*"),
]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Audio Asset Creator")
        self.resizable(False, False)
        self._file_path = tk.StringVar()
        self._build_ui()

    def _build_ui(self):
        file_frame = tk.Frame(self, padx=16, pady=16)
        file_frame.pack(fill="x")

        tk.Label(file_frame, text="Audio File:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        tk.Entry(file_frame, textvariable=self._file_path, width=48, state="readonly").grid(row=0, column=1)
        tk.Button(file_frame, text="Browse", command=self._browse).grid(row=0, column=2, padx=(8, 0))

        tk.Button(self, text="Generate", command=self._generate, padx=20, pady=6).pack(pady=(0, 16))

    def _browse(self):
        path = filedialog.askopenfilename(filetypes=AUDIO_FILETYPES)
        if path:
            self._file_path.set(path)

    def _generate(self):
        path = self._file_path.get()
        if not path:
            messagebox.showwarning("No file selected", "Please select an audio file first.")
            return
        try:
            out = save(path)
            messagebox.showinfo("Done", f"Asset saved to:\n{out}")
        except Exception as e:
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    App().mainloop()
