import tkinter as tk
from tkinter import simpledialog


class CustomUserInputBox(simpledialog.Dialog):
    def __init__(self, parent, **fields):
        self.result = None
        self.fields = fields
        self.entries = {}
        super().__init__(parent, title="Confirm Location")

    def body(self, master):
        for row, (label, value) in enumerate(self.fields.items()):
            tk.Label(master, text=f"{label}:").grid(row=row, column=0)
            entry = tk.Entry(master, width=30)
            entry.grid(row=row, column=1)
            entry.insert(tk.END, value)
            self.entries[label] = entry

    def apply(self):
        self.result = {label: e.get() for label, e in self.entries.items()}
