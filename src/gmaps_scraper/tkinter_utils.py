import tkinter as tk
from tkinter import simpledialog


class CustomUserInputBox(simpledialog.Dialog):
    def __init__(self, parent, fields: dict, missing: list = None):
        """
        fields: dict of label->initial value
        missing: optional list of required field labels that were left blank
        """
        self.result = None
        self.fields = fields
        self.missing = missing or []
        self.entries = {}
        super().__init__(parent, title="Confirm Location")

    def body(self, master):
        row = 0
        # build entry rows
        for label, value in self.fields.items():
            tk.Label(master, text=f"{label}:").grid(row=row, column=0, sticky="w")
            entry = tk.Entry(master, width=30)
            entry.grid(row=row, column=1, sticky="w")
            entry.insert(tk.END, value)
            self.entries[label] = entry
            row += 1

        # if any required fields are missing, show error under entries
        if self.missing:
            err_msg = "Please fill in required fields: " + ", ".join(self.missing)
            tk.Label(master, text=err_msg, fg="red").grid(row=row, columnspan=2, sticky="w")

    def apply(self):
        self.result = {label: entry.get() for label, entry in self.entries.items()}
