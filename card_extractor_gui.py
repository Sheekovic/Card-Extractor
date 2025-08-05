#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tiny Tkinter GUI:
1. Load a .txt file
2. Auto-extract cards (16-digit + 3 CVV OR Amex 15-digit + 4 CVV) + optional balance
3. Sort by balance or BIN prefix (asc)
4. Show results + Save formatted output to a new .txt
"""

import re
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
from pathlib import Path

# --------- REGEXES for extraction ----------
RE_COLON = re.compile(
    r'\b(?P<number>\d{15,16})\s*:\s*'
    r'(?P<mm>\d{2})\s*:\s*'
    r'(?P<yy>\d{2})\s*:\s*'
    r'(?P<cvv>\d{3,4})'
    r'(?:\s*:\s*(?P<balance>[A-Z]{3}\$\d+(?:\.\d{2})?))?'
    r'\b'
)
RE_SLASH = re.compile(
    r'\b(?P<number>\d{15,16})\D+'
    r'(?P<mm>\d{2})/(?P<yy>\d{2})\D+'
    r'(?P<cvv>\d{3,4})'
    r'(?:.*?\b(?P<balance>[A-Z]{3}\$\d+(?:\.\d{2})?))?'
    r'\b',
    re.IGNORECASE
)


def parse_balance(raw: str) -> float:
    if not raw:
        return 0.0
    num = re.sub(r'[^\d\.]', '', raw)
    try:
        return float(num)
    except:
        return 0.0


def luhn_ok(num: str) -> bool:
    total, rev = 0, num[::-1]
    for i, d in enumerate(rev):
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
    return (len(number) == 16 and len(cvv) == 3) or is_amex(number, cvv)


def extract_cards(text: str):
    found, seen = [], set()
    def push(m):
        num = m.group("number")
        mm, yy, cvv = m.group("mm"), m.group("yy"), m.group("cvv")
        bal_raw = m.group("balance") or ""
        key = f"{num}:{mm}:{yy}:{cvv}:{bal_raw}"
        if key in seen:
            return
        if not looks_like_card(num, cvv):
            return
        if not luhn_ok(num):
            return
        seen.add(key)
        found.append({
            "number": num,
            "mm": mm, "yy": yy, "cvv": cvv,
            "balance_raw": bal_raw,
            "balance": parse_balance(bal_raw),
        })
    for m in RE_COLON.finditer(text): push(m)
    for m in RE_SLASH.finditer(text): push(m)
    return found

# --------- GUI ----------
class CardExtractorGUI:
    def __init__(self, root):
        self.root = root
        root.title("Card Extractor – Sort by Balance/BIN")
        root.geometry("900x650")

        self.file_path = tk.StringVar()
        self.cards = []
        self.sort_mode = tk.StringVar(value="balance")  # or 'bin'

        frm_top = ttk.Frame(root, padding=10)
        frm_top.pack(fill="x")
        ttk.Label(frm_top, text="Input file:").pack(side="left")
        ttk.Entry(frm_top, textvariable=self.file_path, width=60).pack(side="left", padx=5)
        ttk.Button(frm_top, text="Browse", command=self.browse_file).pack(side="left")
        ttk.Button(frm_top, text="Extract", command=self.extract).pack(side="left", padx=5)

        frm_sort = ttk.Frame(root, padding=(10,0))
        frm_sort.pack(fill="x")
        ttk.Label(frm_sort, text="Sort by:").pack(side="left")
        ttk.Radiobutton(frm_sort, text="Balance desc", variable=self.sort_mode, value="balance", command=self.resort).pack(side="left", padx=5)
        ttk.Radiobutton(frm_sort, text="BIN asc",     variable=self.sort_mode, value="bin",     command=self.resort).pack(side="left", padx=5)

        frm_mid = ttk.Frame(root, padding=(10,5))
        frm_mid.pack(fill="both", expand=True)
        ttk.Label(frm_mid, text="Extracted cards:").pack(anchor="w")
        self.output_box = scrolledtext.ScrolledText(frm_mid, wrap="none")
        self.output_box.pack(fill="both", expand=True)

        frm_bot = ttk.Frame(root, padding=10)
        frm_bot.pack(fill="x")
        ttk.Button(frm_bot, text="Copy to Clipboard", command=self.copy_clip).pack(side="left")
        ttk.Button(frm_bot, text="Save .txt", command=self.save_file).pack(side="left", padx=5)
        ttk.Button(frm_bot, text="Clear", command=self.clear_output).pack(side="left", padx=5)

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
        p = Path(self.file_path.get().strip())
        if not p.exists():
            messagebox.showerror("Error", "No file selected or file not found.")
            return
        text = p.read_text(encoding="utf-8", errors="ignore")
        self.cards = extract_cards(text)
        if not self.cards:
            self.clear_output()
            self.status_var.set("0 cards found.")
            return
        self.resort()

    def resort(self):
        mode = self.sort_mode.get()
        if mode == "balance":
            lst = sorted(self.cards, key=lambda c: c["balance"], reverse=True)
        else:
            lst = sorted(self.cards, key=lambda c: c["number"])
        self.display(lst)

    def display(self, lst):
        self.output_box.delete("1.0", tk.END)
        for c in lst:
            line = f'{c["number"]}:{c["mm"]}:{c["yy"]}:{c["cvv"]}'
            if c["balance_raw"]:
                line += f':{c["balance_raw"]}'
            self.output_box.insert(tk.END, line+"\n")
        self.status_var.set(f"{len(lst)} card(s) displayed.")

    def copy_clip(self):
        data = self.output_box.get("1.0", tk.END).strip()
        if data:
            self.root.clipboard_clear()
            self.root.clipboard_append(data)
            self.status_var.set("Copied to clipboard.")

    def save_file(self):
        data = self.output_box.get("1.0", tk.END).strip()
        if not data:
            messagebox.showinfo("Nothing to save", "Output is empty.")
            return
        out = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files","*.txt")])
        if out:
            Path(out).write_text(data, encoding="utf-8")
            self.status_var.set(f"Saved to {out}")

    def clear_output(self):
        self.output_box.delete("1.0", tk.END)
        self.status_var.set("Cleared.")

if __name__ == "__main__":
    root = tk.Tk()
    CardExtractorGUI(root)
    root.mainloop()
