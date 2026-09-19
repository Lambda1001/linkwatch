import yaml
from app.schema import create_schema
from app.runner import run_fping
from app.parser import parse_fping_output
from app.db import get_connection, insert_rows

def load_config(path="config.yaml"):
	with open(path) as f:
		return yaml.safe_load(f)

def main():
	cfg = load_config()
	db_path = cfg["db_path"]
	targets = cfg["targets"]
	fping_cfg = cfg.get("fping", {})

	create_schema(db_path)

	ip_to_label = {ip: label for label, ip in targets.items()}
	raw = run_fping(targets, count=fping_cfg.get("count", 4), timeout_ms=fping_cfg.get("timeout_ms", 2000))

	rows = parse_fping_output(raw, ip_to_label)

	if not rows:
		print("No rows parsed")
		return

	conn = get_connection(db_path)

	try:
		insert_rows(conn, rows)
	finally:
		conn.close()

if __name__ == "__main__":
	main()
