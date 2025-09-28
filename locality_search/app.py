import streamlit as st
import sqlite3
import pandas as pd
import difflib
import json, ast   # keep these together

# Parse location field safely
def parse_location(loc_str):
    try:
        return json.loads(loc_str) if isinstance(loc_str, str) else loc_str
    except:
        try:
            return ast.literal_eval(loc_str)
        except:
            return None

# Connect to SQLite (thread-safe)
@st.cache_resource
def get_connection():
    return sqlite3.connect("geoapify_localities.db", check_same_thread=False)

# Query localities (basic LIKE search)
def search_localities(name_query, use_soundex=False, threshold=0.7):
    conn = get_connection()

    if use_soundex:
        query_code = soundex(name_query)
        df = pd.read_sql_query(
            "SELECT name, display_name, location, bbox, type, population, soundex_name FROM localities WHERE soundex_name = ?",
            conn, params=(query_code,)
        )
        df["similarity"] = df["name"].fillna("").apply(
            lambda n: difflib.SequenceMatcher(None, name_query.lower(), n.lower()).ratio()
        )
        return df[df["similarity"] >= threshold]
    else:
        query = """
            SELECT name, display_name, location, bbox, type, population
            FROM localities
            WHERE name LIKE ? OR display_name LIKE ?
        """
        return pd.read_sql_query(query, conn, params=(f"%{name_query}%", f"%{name_query}%"))

# Simple Soundex implementation
import sqlite3

# reuse your Python soundex() function here
def soundex(name, len_code=4):
    if not name: return ""
    name = str(name).upper()
    if not name: return ""
    soundex_mapping = {
        "BFPV": "1", "CGJKQSXZ": "2", "DT": "3",
        "L": "4", "MN": "5", "R": "6"
    }
    first_letter = name[0]
    tail = ""
    for char in name[1:]:
        code = "0"
        for key, val in soundex_mapping.items():
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

# conn = sqlite3.connect("geoapify_localities.db")
# c = conn.cursor()

# # Add column if not exists
# try:
#     c.execute("ALTER TABLE localities ADD COLUMN soundex_name TEXT")
# except sqlite3.OperationalError:
#     pass  # already exists

# # Update rows with precomputed soundex
# rows = c.execute("SELECT rowid, name FROM localities").fetchall()
# for rowid, name in rows:
#     sx = soundex(name)
#     c.execute("UPDATE localities SET soundex_name = ? WHERE rowid = ?", (sx, rowid))

# conn.commit()
# conn.close()

# Streamlit UI
st.title("🌍 Localities Explorer with Soundex Search")
st.write("Search for a locality by exact name or by how it sounds.")

name_query = st.text_input("Enter locality name:")
use_soundex = st.checkbox("Use Soundex (find similar sounding names)")
threshold = st.slider("Similarity threshold (0–1)", 0.0, 1.0, 0.7)

if name_query:
    df = search_localities(name_query)

    if use_soundex:
        query_code = soundex(name_query)
        df["soundex"] = df["name"].fillna("").apply(soundex)
        df["similarity"] = df["name"].fillna("").apply(
            lambda n: difflib.SequenceMatcher(None, name_query.lower(), n.lower()).ratio()
        )
        results = df[(df["soundex"] == query_code) & (df["similarity"] >= threshold)]
    else:
        results = df[
            df["name"].str.contains(name_query, case=False, na=False) |
            df["display_name"].str.contains(name_query, case=False, na=False)
        ]

    if not results.empty:
        # Parse coords
        results["coords"] = results["location"].apply(parse_location)
        results[["lon", "lat"]] = pd.DataFrame(results["coords"].tolist(), index=results.index)

        st.write(f"Found {len(results)} matching localities:")
        st.dataframe(results[["name", "display_name", "type", "population", "similarity"]] if use_soundex else results[["name", "display_name", "type", "population"]])

        st.map(results[["lat", "lon"]])
    else:
        st.warning("No localities found.")
