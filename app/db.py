import sqlite3

def get_connection(db_path: str)->sqlite3.Connection:
	return sqlite3.connect(db_path)

def insert_rows(conn: sqlite3.Connection, rows: list[dict]):
	conn.executemany(
		"""
		INSERT INTO pings(ts, target_label, target_ip, success, rtt_min, rtt_avg, rtt_max, packet_loss_pct)
		VALUES(:ts, :target_label, :target_ip, :success, :rtt_min, :rtt_avg, :rtt_max, :packet_loss_pct)
		""",
		rows
	)
	conn.commit()
