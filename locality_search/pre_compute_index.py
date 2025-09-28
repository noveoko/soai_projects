# precompute_soundex.py
import sqlite3

def soundex(name, len_code=4):
    if not name: return ""
    name = str(name).upper()
    if not name: return ""
    mapping = {"BFPV": "1", "CGJKQSXZ": "2", "DT": "3", "L": "4", "MN": "5", "R": "6"}
    first_letter = name[0]
    tail = ""
    for char in name[1:]:
        code = "0"
        for key, val in mapping.items():
            if char in key:
                code = val
                break
        tail += code
    prev, tail2 = "", ""
    for char in tail:
        if char != prev and char != "0":
            tail2 += char
        prev = char
    return (first_letter + tail2 + "0000")[:len_code]

conn = sqlite3.connect("geoapify_localities.db")
c = conn.cursor()

try:
    c.execute("ALTER TABLE localities ADD COLUMN soundex_name TEXT")
except sqlite3.OperationalError:
    pass  # already exists

rows = c.execute("SELECT rowid, name FROM localities").fetchall()
for rowid, name in rows:
    sx = soundex(name)
    c.execute("UPDATE localities SET soundex_name = ? WHERE rowid = ?", (sx, rowid))

# 🚀 Add index for speed
c.execute("CREATE INDEX IF NOT EXISTS idx_soundex_name ON localities(soundex_name)")

conn.commit()
conn.close()
print("✅ Soundex precomputation done.")
