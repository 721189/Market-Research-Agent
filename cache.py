import sqlite3
import hashlib
import json
import os

# Database file location (creates a file called 'cache.db' in your project root)
DB_PATH = os.path.join(os.path.dirname(__file__), "cache.db")

def init_db():
    """Create the cache table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            query_hash TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            result TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_cached(query: str):
    """Check if we have a cached result for this query."""
    init_db()  # Ensure the table exists before querying
    
    query_hash = hashlib.md5(query.encode()).hexdigest()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT result FROM cache WHERE query_hash = ?", 
        (query_hash,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return json.loads(row[0])  # Return the cached result
    return None

# <--- FIXED: Renamed this from 'set_cache' to 'set_cached' to match your main.py --->
def set_cached(query: str, result: dict):
    """Store the result in the cache."""
    init_db()  # Ensure the table exists before inserting
    
    query_hash = hashlib.md5(query.encode()).hexdigest()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO cache (query_hash, query, result) VALUES (?, ?, ?)",
        (query_hash, query, json.dumps(result))
    )
    conn.commit()
    conn.close()

def clear_cache():
    """Delete everything in the cache (useful for debugging)."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM cache")
    conn.commit()
    conn.close()