import tkinter as tk
from tkinter import simpledialog


class CustomUserInputBox(simpledialog.Dialog):
    def __init__(self, parent, **kwargs):
        self.result = None
        self.kwargs = kwargs
        self.entries = {}
        super().__init__(parent, title="Confirm Location")

        self.kwargs = kwargs

    def body(self, master):
        row = 0
        for key, value in self.kwargs.items():
            tk.Label(master, text=key + ":").grid(row=row, column=0)
            entry = tk.Entry(master, width=30)
            entry.grid(row=row, column=1)
            entry.insert(tk.END, value)
            self.entries[key] = entry
            row += 1

    def apply(self):
        self.result = {key: entry.get() for key, entry in self.entries.items()}
