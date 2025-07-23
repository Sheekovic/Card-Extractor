# Card Extractor GUI

Because manually eyeballing `4358807872436900:02:33:542` out of a swamp of tabs and colons is not a personality trait.

## What it does

- **Loads any .txt file** full of chaotic logs.
- **Extracts cards** in the format:  
  `number:MM:YY:CVV`
  - Visa/Master/etc.: 16 digits + 3‑digit CVV  
  - **Amex**: 15 digits (starts with 34/37) + 4‑digit CVV (e.g. `373778893437830:06:36:5853`)
- Accepts both **strict `:` separated** and **messy random junk** between parts.
- **Luhn check** to kill false positives.
- Lets you **copy** or **save** the clean list as a new `.txt`.

## Screenshot (in your imagination)

```

## \[ Browse ] \[ Extract ]                  Status: 42 card(s) found.

4358807872436900:02:33:542
373778893437830:06:36:5853
...
---

\[ Copy to Clipboard ] \[ Save .txt ] \[ Clear ]

````

## Requirements

- Python 3.8+ (you’ve got 3.13, flex on ‘em)
- Built‑in modules only (Tkinter ships with Python).

## Install & Run

```bash
git clone https://github.com/yourrepo/card-extractor-gui.git
cd card-extractor-gui
python card_extractor_gui.py
````

> Windows double-clickers: just double-click it.
> Linux/Mac: same deal, plus your terminal swagger.

## The Regex Magic

```python
PATTERN_STRICT = r'\b(?P<number>\d{15,16})\s*:\s*(?P<mm>\d{2})\s*:\s*(?P<yy>\d{2})\s*:\s*(?P<cvv>\d{3,4})\b'
PATTERN_FLEX   = r'\b(?P<number>\d{15,16})\D+(?P<mm>\d{2})\D+(?P<yy>\d{2})\D+(?P<cvv>\d{3,4})\b'
```

* We try **strict** first (to avoid trash).
* Then a **flex** fallback for weird separators.
* We dedupe, validate, and only keep sane matches.

## Build an EXE (optional)

Using `pyinstaller`:

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole card_extractor_gui.py
dist/card_extractor_gui.exe
```

Now you can send it to your friend who still thinks `pip` is a plumbing term.

## Folder Structure

```
card-extractor-gui/
├─ card_extractor_gui.py
├─ README.md
└─ (dist/, build/, etc. if you compile)
```

## Roadmap / TODO (a.k.a. “feature creep ideas”)

* Export to CSV / XLSX with BIN, brand detection.
* Real-time paste watcher (clipboard sniffer).
* Drag & drop files onto the window.
* Filters: balance ranges, BIN lists, whatever your empire needs.

## License

MIT. Do whatever, just don’t blame me when you parse your grocery receipt and think you found a Black Card.