import sqlite3

def get_connection(db_path: str) -> sqlite3.Connection:
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	return conn

def latest_status(conn) -> list[sqlite3.Row]:
	return conn.execute("""
		SELECT target_label, target_ip, success, rtt_avg, packet_loss_pct, ts
		FROM pings
		WHERE ts = (SELECT MAX(ts) FROM pings)
		ORDER BY target_label
	""").fetchall()

def summary(conn, hours: int = 24) -> list[sqlite3.Row]:
	return conn.execute("""
		SELECT target_label,
			ROUND(AVG(rtt_avg), 1) AS "Average RTT",
			ROUND(MIN(rtt_min), 1) AS "Min RTT",
			ROUND(MAX(rtt_max), 1) AS "Max RTT",
			ROUND(AVG(packet_loss_pct), 1) AS "Average Packet Loss",
			COUNT (*) AS samples
		FROM pings
		WHERE ts > strftime('%s', 'now', ?)
		GROUP BY target_label
	""", (f"-{hours} hours",)).fetchall()

def recent_outages(conn, hours: int = 24, loss_threshold: float = 50.0) -> list[sqlite3.Row]:
	return conn.execute("""
		SELECT target_label, target_ip, ts, packet_loss_pct
		FROM pings
		WHERE ts > strftime('%s', 'now', ?)
		AND packet_loss_pct >= ?
		ORDER BY ts DESC
	""", (f"-{hours} hours", loss_threshold)).fetchall()

def history(conn, target_label: str, bucket_minutes: int,hours: int = 24)-> list[sqlite3.Row]:
	seconds = bucket_minutes * 60
	return conn.execute("""
		SELECT (ts/?) * ? AS bucket, target_label,
			ROUND(AVG(rtt_avg), 1) as "Average RTT",
			ROUND(MIN(rtt_min), 1) AS "Min RTT",
			ROUND(MAX(rtt_max), 1) AS "Max RTT"
		FROM pings
		WHERE target_label = ?
		AND ts > strftime('%s', 'now', ?)
		GROUP BY bucket
		ORDER BY bucket ASC;
	""", (seconds, seconds, target_label, f"-{hours} hours")).fetchall()
