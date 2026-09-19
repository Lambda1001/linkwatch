import re
import time

LINE_RE = re.compile(
    r"^(?P<ip>\S+)\s*:\s*"
    r"xmt/rcv/%loss = \d+/\d+/(?P<loss>\d+)%"
    r"(?:,\s*min/avg/max = (?P<min>[\d.]+)/(?P<avg>[\d.]+)/(?P<max>[\d.]+))?"
)

def parse_fping_output(output: str, ip_to_label: dict)-> list[dict]:
	ts =  int(time.time())
	rows = []

	for line in output.strip().splitlines():
		match = LINE_RE.match(line.strip())
		if not match:
			continue
		ip = match.group("ip")
		loss = float(match.group("loss"))
		success = 1 if loss < 100 else 0

		rows.append({
			"ts": ts,
			"target_label": ip_to_label.get(ip, "unknown"),
			"target_ip": ip,
			"success": success,
			"rtt_min": float(match.group("min")) if match.group("min") else None,
			"rtt_avg": float(match.group("avg")) if match.group("avg") else None,
			"rtt_max": float(match.group("max")) if match.group("max") else None,
			"packet_loss_pct": loss

		})

	return rows

if __name__ == "__main__":
	sample = """8.8.8.8 : xmt/rcv/%loss = 4/4/0%, min/avg/max = 12.1/13.4/15.0
 1.1.1.1 : xmt/rcv/%loss = 4/0/100%"""
	ip_map = {"8.8.8.8": "google_dns", "1.1.1.1": "cloudflare"}
	for row in parse_fping_output(sample, ip_map):
		print(row)
