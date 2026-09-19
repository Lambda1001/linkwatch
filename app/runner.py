import subprocess

def run_fping(targets: dict, count: int=4, timeout_ms: int=2000) -> str:
	ips = list(targets.values())
	cmd = ["fping", "-c", str(count), "-t", str(timeout_ms), "-q"] + ips
	
	results = subprocess.run(cmd, capture_output=True, text=True)
	return results.stderr

if __name__ == "__main__":
	targets = {"google_dns": "8.8.8.8", "cloudflare": "1.1.1.1"}
	print(run_fping(targets))
