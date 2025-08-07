import re
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
from pathlib import Path

# --------- BALANCE PATTERN ----------
BAL_PATTERN = r'(?:[A-Z]{1,3})?\$\d+(?:\.\d{2})?|\d+,\d+'

# --------- REGEXES for extraction ----------
RE_COLON = re.compile(
    rf"\b(?P<number>\d{{15,16}})\s*:\s*"
    rf"(?P<mm>\d{{2}})\s*:\s*"
    rf"(?P<yy>\d{{2}})\s*:\s*"
    rf"(?P<cvv>\d{{3,4}})"
    rf"(?:\s*:\s*(?P<balance>{BAL_PATTERN}))?"
    rf"\b"
)
RE_SLASH = re.compile(
    rf"\b(?P<number>\d{{15,16}})\D+"
    rf"(?P<mm>\d{{2}})/(?P<yy>\d{{2}})\D+"
    rf"(?P<cvv>\d{{3,4}})"
    rf"(?:.*?\b(?P<balance>{BAL_PATTERN}))?"
    rf"\b",
    re.IGNORECASE
)
EU_LINE = re.compile(r"^\s*\d+(?:,\d+)?\s*$")

# priority for currency sorting
CURRENCY_PRIORITY = {"USD": 0, "CAD": 1, "AUD": 2}

def parse_balance(raw: str) -> tuple[float, str]:
    """
    Parse raw balance from formats:
    - 'CAD$10.31', '$1.95', 'US$46.14', 'CAD$82.23'
    - EU comma '88,8', '87,88'
    - Plain integer '200'
    Returns (value, currency). Defaults currency to USD if unspecified.
    """
    raw = (raw or '').strip()
    if '|' in raw:
        raw = raw.rsplit('|', 1)[-1].strip()
    raw = re.sub(r'(?i)^balance\s+', '', raw).strip()
    # EU decimal
    if re.match(r"^\d+,\d+$", raw):
        return float(raw.replace(',', '.')), 'USD'
    # Plain integer
    if re.match(r"^\d+$", raw):
        return float(raw), 'USD'
    # currency$amount or $amount
    m = re.match(r"^(?P<cur>[A-Z]{1,3})?\$(?P<amt>\d+(?:\.\d{2})?)$", raw)
    if m:
        cur = m.group('cur') or 'USD'
        return float(m.group('amt')), cur
    # fallback: extract digits and dot
    num = re.sub(r'[^\d\.]', '', raw)
    try:
        return float(num), 'USD'
    except:
        return 0.0, ''

def extract_cards(text: str) -> list[dict]:
    """
    Robust extractor: Handles single-line and multi-line balances,
    plus inline/junk tokens and trailing tokens.
    """
    found, seen = [], set()
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # 1. Try colon (preferred) or slash patterns
        m = RE_COLON.search(line) or RE_SLASH.search(line)
        if m:
            num = m.group('number')
            mm, yy, cvv = m.group('mm'), m.group('yy'), m.group('cvv')
            bal_raw = (m.group('balance') or '').strip()
            # If no inline balance, look for one after colon, pipe, or 'balance' in line
            if not bal_raw:
                # Look for balance token after any separator or anywhere in line
                extra = line.split(':', 4)[-1]
                bal_match = re.search(r'([A-Z]{1,3})?\$\d+(?:\.\d{2})?', extra)
                if not bal_match:
                    bal_match = re.search(r'(\d+,\d+)', extra)
                if not bal_match:
                    # Also try full line (catch things like "| $100.00" or "balance CAD$82.23 ...")
                    bal_match = re.search(r'([A-Z]{1,3})?\$\d+(?:\.\d{2})?|(\d+,\d+)', line)
                if bal_match:
                    bal_raw = bal_match.group(0)
            # If still no balance, check next line (EU style)
            if not bal_raw and i + 1 < len(lines):
                nextline = lines[i + 1].strip()
                if re.fullmatch(r'\d+,\d+', nextline):
                    bal_raw = nextline
                    i += 1  # skip next line
            key = f"{num}:{mm}:{yy}:{cvv}:{bal_raw}"
            if key in seen or not looks_like_card(num, cvv) or not luhn_ok(num):
                i += 1
                continue
            val, cur = parse_balance(bal_raw)
            seen.add(key)
            found.append({
                'number': num, 'mm': mm, 'yy': yy, 'cvv': cvv,
                'balance_raw': bal_raw, 'balance': val, 'currency': cur
            })
        i += 1
    return found

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

# --------- GUI ----------
class CardExtractorGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title('Card Extractor – Enhanced')
        root.geometry('900x750')

        self.file_path = tk.StringVar()
        self.cards: list[dict] = []
        self.sort_mode = tk.StringVar(value='balance')

        # Top controls
        top = ttk.Frame(root, padding=10)
        top.pack(fill='x')
        ttk.Label(top, text='Input file:').pack(side='left')
        ttk.Entry(top, textvariable=self.file_path, width=60).pack(side='left', padx=5)
        ttk.Button(top, text='Browse', command=self.browse_file).pack(side='left')
        ttk.Button(top, text='Extract', command=self.extract).pack(side='left', padx=5)

        # Sort options
        opts = ttk.Frame(root, padding=(10,5))
        opts.pack(fill='x')
        ttk.Label(opts, text='Sort by:').pack(side='left')
        ttk.Radiobutton(opts, text='Balance ↓', variable=self.sort_mode, value='balance', command=self.resort).pack(side='left', padx=5)
        ttk.Radiobutton(opts, text='BIN ↑',     variable=self.sort_mode, value='bin',     command=self.resort).pack(side='left', padx=5)
        ttk.Radiobutton(opts, text='Currency',  variable=self.sort_mode, value='currency', command=self.resort).pack(side='left', padx=5)

        # Display
        mid = ttk.Frame(root, padding=(10,5))
        mid.pack(fill='both', expand=True)
        ttk.Label(mid, text='Extracted cards:').pack(anchor='w')
        self.output_box = scrolledtext.ScrolledText(mid, wrap='none')
        self.output_box.pack(fill='both', expand=True)

        # Bottom
        bot = ttk.Frame(root, padding=10)
        bot.pack(fill='x')
        ttk.Button(bot, text='Copy to Clipboard', command=self.copy_clip).pack(side='left')
        ttk.Button(bot, text='Save .txt', command=self.save_file).pack(side='left', padx=5)
        ttk.Button(bot, text='Clear', command=self.clear_output).pack(side='left', padx=5)

        self.status = tk.StringVar(value='Ready.')
        ttk.Label(root, textvariable=self.status, anchor='w').pack(fill='x', padx=10, pady=(0,10))

    def browse_file(self):
        path = filedialog.askopenfilename(filetypes=[('Text files','*.txt'),('All','*.*')])
        if path:
            self.file_path.set(path)

    def extract(self):
        p = Path(self.file_path.get().strip())
        if not p.exists():
            messagebox.showerror('Error','No file selected or file not found.')
            return
        text = p.read_text(encoding='utf-8', errors='ignore')
        self.cards = extract_cards(text)
        if not self.cards:
            self.clear_output()
            self.status.set('0 cards found.')
            return
        self.resort()

    def resort(self):
        mode = self.sort_mode.get()
        if mode=='balance':
            ordered = sorted(self.cards, key=lambda c: c['balance'], reverse=True)
        elif mode=='bin':
            ordered = sorted(self.cards, key=lambda c: c['number'])
        else:
            ordered = sorted(self.cards, key=lambda c: (CURRENCY_PRIORITY.get(c['currency'],99), -c['balance']))
        self.display(ordered)

    def display(self, data: list[dict]):
        self.output_box.delete('1.0',tk.END)
        for c in data:
            line = f"{c['number']}:{c['mm']}:{c['yy']}:{c['cvv']}"
            if c['balance_raw']:
                line += f":{c['balance_raw']}"
            self.output_box.insert(tk.END, line+'\n')
        self.status.set(f"{len(data)} card(s) displayed.")

    def copy_clip(self):
        txt = self.output_box.get('1.0',tk.END).strip()
        if txt:
            self.root.clipboard_clear()
            self.root.clipboard_append(txt)
            self.status.set('Copied to clipboard.')

    def save_file(self):
        txt = self.output_box.get('1.0',tk.END).strip()
        if not txt:
            messagebox.showinfo('Nothing to save','Output is empty.')
            return
        out = filedialog.asksaveasfilename(defaultextension='.txt',filetypes=[('Text files','*.txt')])
        if out:
            Path(out).write_text(txt,encoding='utf-8')
            self.status.set(f"Saved to {out}")

    def clear_output(self):
        self.output_box.delete('1.0',tk.END)
        self.status.set('Cleared.')

if __name__=='__main__':
    root=tk.Tk()
    CardExtractorGUI(root)
    root.mainloop()
