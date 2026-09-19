import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS pings(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 ts INTEGER NOT NULL,
 target_label TEXT NOT NULL,
 target_ip TEXT NOT NULL,
 success INTEGER NOT NULL,
 rtt_min REAL,
 rtt_avg REAL,
 rtt_max REAL,
 packet_loss_pct REAL
);

CREATE INDEX IF NOT EXISTS idx_ts_target ON pings(ts, target_label);
"""

def create_schema(db_path: str):
	conn = sqlite3.connect(db_path)
	try:
		conn.executescript(SCHEMA)
		conn.commit()
	finally:
		conn.close()

if __name__ == "__main__":
	create_schema("data/pings.db")
	print("Schema created")
