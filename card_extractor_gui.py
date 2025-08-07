#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tiny Tkinter GUI:
1. Load a .txt file
2. Auto-extract cards (16-digit + 3 CVV OR Amex 15-digit + 4 CVV) + optional balance
3. Sort by balance, BIN prefix, or currency order (USD, CAD, AUD)
4. Show results + Save formatted output to a new .txt
"""

import re
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
from pathlib import Path

# --------- REGEXES for extraction ----------
# capture optional 3-letter code or none before $amount
RE_COLON = re.compile(
    r"\b(?P<number>\d{15,16})\s*:\s*"
    r"(?P<mm>\d{2})\s*:\s*"
    r"(?P<yy>\d{2})\s*:\s*"
    r"(?P<cvv>\d{3,4})"
    r"(?:\s*:\s*(?P<balance>(?:[A-Z]{3})?\$\d+(?:\.\d{2})?))?"
    r"\b"
)
RE_SLASH = re.compile(
    r"\b(?P<number>\d{15,16})\D+"
    r"(?P<mm>\d{2})/(?P<yy>\d{2})\D+"
    r"(?P<cvv>\d{3,4})"
    r"(?:.*?\b(?P<balance>(?:[A-Z]{3})?\$\d+(?:\.\d{2})?))?"
    r"\b",
    re.IGNORECASE
)

# priority for currency sorting
CURRENCY_PRIORITY = {"USD": 0, "CAD": 1, "AUD": 2}


def parse_balance(raw: str) -> tuple[float, str]:
    """
    Parse raw balance like 'CAD$10.31', '$1.95', or '| $1.95'.
    Returns (value: float, currency: str).
    """
    raw = (raw or "").strip()
    if not raw:
        return 0.0, ""
    # match optional 3-letter currency + $ + amount
    m = re.match(r'^(?P<cur>[A-Z]{3})?\$(?P<amt>\d+(?:\.\d{2})?)$', raw)
    if m:
        currency = m.group('cur') or 'USD'
        amount = float(m.group('amt'))
        return amount, currency
    # fallback: extract number, assume USD
    num = re.sub(r'[^\d\.]', '', raw)
    try:
        return float(num), 'USD'
    except ValueError:
        return 0.0, ''


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


def extract_cards(text: str) -> list[dict]:
    """
    Extract card entries with optional balances from text.
    Returns list of dicts with keys number, mm, yy, cvv, balance_raw, balance, currency.
    """
    found, seen = [], set()
    def push(match: re.Match):
        num = match.group("number")
        mm, yy, cvv = match.group("mm"), match.group("yy"), match.group("cvv")
        bal_raw = match.group("balance") or ""
        key = f"{num}:{mm}:{yy}:{cvv}:{bal_raw}"
        if key in seen:
            return
        if not looks_like_card(num, cvv) or not luhn_ok(num):
            return
        value, currency = parse_balance(bal_raw)
        seen.add(key)
        found.append({
            "number": num,
            "mm": mm,
            "yy": yy,
            "cvv": cvv,
            "balance_raw": bal_raw,
            "balance": value,
            "currency": currency,
        })
    for m in RE_COLON.finditer(text):
        push(m)
    for m in RE_SLASH.finditer(text):
        push(m)
    return found

# --------- GUI ----------
class CardExtractorGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Card Extractor – Multi-sort Mode")
        root.geometry("900x700")

        self.file_path = tk.StringVar()
        self.cards: list[dict] = []
        self.sort_mode = tk.StringVar(value="balance")  # options: 'balance', 'bin', 'currency'

        # Top controls
        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Input file:").pack(side="left")
        ttk.Entry(top, textvariable=self.file_path, width=60).pack(side="left", padx=5)
        ttk.Button(top, text="Browse", command=self.browse_file).pack(side="left")
        ttk.Button(top, text="Extract", command=self.extract).pack(side="left", padx=5)

        # Sort options
        opts = ttk.Frame(root, padding=(10, 5))
        opts.pack(fill="x")
        ttk.Label(opts, text="Sort by:").pack(side="left")
        ttk.Radiobutton(opts, text="Balance ↓", variable=self.sort_mode, value="balance", command=self.resort).pack(side="left", padx=5)
        ttk.Radiobutton(opts, text="BIN ↑",     variable=self.sort_mode, value="bin",      command=self.resort).pack(side="left", padx=5)
        ttk.Radiobutton(opts, text="Currency",  variable=self.sort_mode, value="currency", command=self.resort).pack(side="left", padx=5)

        # Display area
        mid = ttk.Frame(root, padding=(10, 5))
        mid.pack(fill="both", expand=True)
        ttk.Label(mid, text="Extracted cards:").pack(anchor="w")
        self.output_box = scrolledtext.ScrolledText(mid, wrap="none")
        self.output_box.pack(fill="both", expand=True)

        # Bottom controls
        bot = ttk.Frame(root, padding=10)
        bot.pack(fill="x")
        ttk.Button(bot, text="Copy to Clipboard", command=self.copy_clip).pack(side="left")
        ttk.Button(bot, text="Save .txt", command=self.save_file).pack(side="left", padx=5)
        ttk.Button(bot, text="Clear", command=self.clear_output).pack(side="left", padx=5)

        self.status = tk.StringVar(value="Ready.")
        ttk.Label(root, textvariable=self.status, anchor="w").pack(fill="x", padx=10, pady=(0,10))

    def browse_file(self):
        path = filedialog.askopenfilename(title="Select text file", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            self.file_path.set(path)

    def extract(self):
        p = Path(self.file_path.get().strip())
        if not p.exists():
            messagebox.showerror("Error", "No file selected or file not found.")
            return
        txt = p.read_text(encoding="utf-8", errors="ignore")
        self.cards = extract_cards(txt)
        if not self.cards:
            self.clear_output()
            self.status.set("0 cards found.")
            return
        self.resort()

    def resort(self):
        mode = self.sort_mode.get()
        if mode == "balance":
            ordered = sorted(self.cards, key=lambda c: c["balance"], reverse=True)
        elif mode == "bin":
            ordered = sorted(self.cards, key=lambda c: c["number"])
        else:  # currency
            ordered = sorted(
                self.cards,
                key=lambda c: (CURRENCY_PRIORITY.get(c["currency"], 99), -c["balance"])
            )
        self.display(ordered)

    def display(self, data: list[dict]):
        self.output_box.delete("1.0", tk.END)
        for c in data:
            line = f"{c['number']}:{c['mm']}:{c['yy']}:{c['cvv']}"
            if c['balance_raw']:
                line += f":{c['balance_raw']}"
            self.output_box.insert(tk.END, line + "\n")
        self.status.set(f"{len(data)} card(s) displayed.")

    def copy_clip(self):
        text = self.output_box.get("1.0", tk.END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status.set("Copied to clipboard.")

    def save_file(self):
        text = self.output_box.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("Nothing to save", "Output is empty.")
