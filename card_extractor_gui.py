#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tiny Tkinter GUI:
1. Load a .txt file
2. Auto-extract cards (16‑digit + 3 CVV OR Amex 15‑digit + 4 CVV)
3. Show results
4. Save formatted output to a new .txt
"""

import re
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
from pathlib import Path

# --------- REGEXES ----------
# Strict colon-separated pattern first (preferred)
PATTERN_STRICT = re.compile(
    r'\b(?P<number>\d{15,16})\s*:\s*(?P<mm>\d{2})\s*:\s*(?P<yy>\d{2})\s*:\s*(?P<cvv>\d{3,4})\b'
)

# Fallback: anything non-digit between segments (guards against junk separators)
PATTERN_FLEX = re.compile(
    r'\b(?P<number>\d{15,16})\D+(?P<mm>\d{2})\D+(?P<yy>\d{2})\D+(?P<cvv>\d{3,4})\b'
)

def luhn_ok(num: str) -> bool:
    """Luhn check to reduce false positives."""
    total = 0
    reverse_digits = num[::-1]
    for i, d in enumerate(reverse_digits):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0

def is_amex(number: str, cvv: str) -> bool:
    return len(number) == 15 and number.startswith(("34", "37")) and len(cvv) == 4

def looks_like_card(number: str, cvv: str) -> bool:
    # Accept:
    # - 16-digit with 3 CVV
    # - Amex (15-digit starting 34/37) with 4 CVV
    return (len(number) == 16 and len(cvv) == 3) or is_amex(number, cvv)

def extract_cards(text: str):
    found = []
    seen = set()

    def push(m):
        number = m.group("number")
        mm = m.group("mm")
        yy = m.group("yy")
        cvv = m.group("cvv")

        key = f"{number}:{mm}:{yy}:{cvv}"
        if key in seen:
            return
        if not looks_like_card(number, cvv):
            return
        if not luhn_ok(number):
            return
        seen.add(key)
        found.append(key)

    # Try strict first
    for m in PATTERN_STRICT.finditer(text):
        push(m)

    # Then flex (only if we didn't already capture it)
    for m in PATTERN_FLEX.finditer(text):
        push(m)

    return found

# --------- GUI ----------
class CardExtractorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Card Extractor – because parsing by hand is overrated")
        self.root.geometry("800x600")

        self.file_path = tk.StringVar()

        frm_top = ttk.Frame(root, padding=10)
        frm_top.pack(fill="x")

        ttk.Label(frm_top, text="Input file:").pack(side="left")
        ttk.Entry(frm_top, textvariable=self.file_path, width=60).pack(side="left", padx=5)
        ttk.Button(frm_top, text="Browse", command=self.browse_file).pack(side="left")
        ttk.Button(frm_top, text="Extract", command=self.extract).pack(side="left", padx=5)

        frm_mid = ttk.Frame(root, padding=(10, 0, 10, 5))
        frm_mid.pack(fill="both", expand=True)

        ttk.Label(frm_mid, text="Extracted cards:").pack(anchor="w")
        self.output_box = scrolledtext.ScrolledText(frm_mid, wrap="none", height=20)
        self.output_box.pack(fill="both", expand=True)

        frm_bottom = ttk.Frame(root, padding=10)
        frm_bottom.pack(fill="x")
        ttk.Button(frm_bottom, text="Copy to Clipboard", command=self.copy_clip).pack(side="left")
        ttk.Button(frm_bottom, text="Save .txt", command=self.save_file).pack(side="left", padx=5)
        ttk.Button(frm_bottom, text="Clear", command=self.clear_output).pack(side="left", padx=5)

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(root, textvariable=self.status_var, anchor="w").pack(fill="x", padx=10, pady=(0,10))

    def browse_file(self):
        path = filedialog.askopenfilename(
            title="Select text file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.file_path.set(path)

    def extract(self):
        path = self.file_path.get().strip()
        if not path:
            messagebox.showwarning("No file", "Pick a file first.")
            return
        p = Path(path)
        if not p.exists():
            messagebox.showerror("File not found", f"{p}")
            return
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            messagebox.showerror("Read error", str(e))
            return

        cards = extract_cards(text)
        self.output_box.delete("1.0", tk.END)
        if not cards:
            self.output_box.insert(tk.END, "No cards found. Try again (or your source is garbage).")
            self.status_var.set("0 cards found.")
            return

        self.output_box.insert(tk.END, "\n".join(cards))
        self.status_var.set(f"{len(cards)} card(s) found.")

    def copy_clip(self):
        data = self.output_box.get("1.0", tk.END).strip()
        if not data:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(data)
        self.status_var.set("Copied to clipboard.")

    def save_file(self):
        data = self.output_box.get("1.0", tk.END).strip()
        if not data:
            messagebox.showinfo("Nothing to save", "Output is empty.")
            return
        out_path = filedialog.asksaveasfilename(
            title="Save formatted cards",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")]
        )
        if not out_path:
            return
        try:
            Path(out_path).write_text(data, encoding="utf-8")
            self.status_var.set(f"Saved to {out_path}")
        except Exception as e:
            messagebox.showerror("Write error", str(e))

    def clear_output(self):
        self.output_box.delete("1.0", tk.END)
        self.status_var.set("Cleared.")

def main():
    root = tk.Tk()
    CardExtractorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
