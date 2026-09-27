import yaml
import argparse
import sys
import time
from importlib.metadata import version
from rich_argparse import RichHelpFormatter
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.live import Live

from app.queries import get_connection, summary, latest_status, recent_outages, history


def load_cfg(path = "config.yaml"):
	with open(path) as f:
		return yaml.safe_load(f)

console = Console()
cfg = load_cfg()
DB_PATH = cfg["db_path"]

def render_status_table(conn) -> Table:
	table = Table(title="Linkwatch - Latest Status")
	table.add_column("Target")
	table.add_column("IP")
	table.add_column("Status")
	table.add_column("RTT (ms)")
	table.add_column("Loss(%)")

	for row in latest_status(conn):
		status = "[green]UP[/]" if row["success"] else "[red]DOWN[/]"
		rtt = f"{row['rtt_avg']:.1f}" if row["rtt_avg"] is not None else "-"
		table.add_row(row["target_label"], row["target_ip"], status, rtt, f"{row['packet_loss_pct']:.0f}%")

	return table

def cmd_status(args):
	conn = get_connection(DB_PATH)
	console.print(render_status_table(conn))

def cmd_watch(args):
	conn = get_connection(DB_PATH)
	with Live(render_status_table(conn), refresh_per_second=1, console=console) as live:
		while True:
			time.sleep(args.interval)
			live.update(render_status_table(conn))

def cmd_summary(args):
	conn = get_connection(DB_PATH)
	table = Table(title=f"Summary - Last {args.hours} hrs")
	table.add_column("Target")
	table.add_column("Avg RTT")
	table.add_column("Max RTT")
	table.add_column("Min RTT")
	table.add_column("Avg Loss")
	table.add_column("Samples")

	for row in summary(conn, args.hours):
		table.add_row(
			row["target_label"],
			f"{row['Average RTT']}" if row['Average RTT'] is not None else "-",
			f"{row['Max RTT']}" if row['Max RTT'] is not None else "-",
			f"{row['Min RTT']}" if row['Min RTT'] is not None else "-",
			f"{row['Average Packet Loss']}%",
			str(row['samples']),
		)
	console.print(table)

def cmd_outages(args):
    conn = get_connection(DB_PATH)
    rows = recent_outages(conn, args.hours, args.threshold)
    if not rows:
        console.print(f"[green]No outages ≥{args.threshold}% loss in the last {args.hours}h.[/]")
        return

    table = Table(title=f"Outages — last {args.hours}h (≥{args.threshold}% loss)")
    table.add_column("Time")
    table.add_column("Target")
    table.add_column("Loss %")
    for row in rows:
        ts_str = datetime.fromtimestamp(row["ts"]).strftime("%Y-%m-%d %H:%M:%S")
        table.add_row(ts_str, row["target_label"], f"{row['packet_loss_pct']:.0f}%")
    console.print(table)

def cmd_history(args):
	conn = get_connection(DB_PATH)

	table = Table(title=f"Test Ping History - within {args.bucket_minutes} minutes for the last {args.hours}h")
	table.add_column("Timestamp")
	table.add_column("Target")
	table.add_column("Average RTT")
	table.add_column("Min RTT")
	table.add_column("Max RTT")

	for row in history(conn, bucket_minutes=args.bucket_minutes, target_label=args.target, hours=args.hours):
		ts_str=datetime.fromtimestamp(row["bucket"]).strftime("%Y-%m-%d %H:%M:%S")
		table.add_row(
			ts_str,
			row["target_label"],
			f"{row['Average RTT']}" if row['Average RTT'] is not None else "-",
			f"{row['Min RTT']}" if row['Min RTT'] is not None else "-",
			f"{row['Max RTT']}" if row['Max RTT'] is not None else "-",
		)
	console.print(table)


def main():
	parser = argparse.ArgumentParser(prog="linkwatch", description="Linkwatch - Terminal-based network target latency monitor",
			epilog=(
				"Examples:\n"
				"linkwatch status\n"
				"linkwatch summary --hours 12\n"
				"linkwatch outages --hours 48 --threshold 25\n"
				"linkwatch watch --interval 5\n"
				),
		formatter_class=RichHelpFormatter,	)

	parser.add_argument("--version", action="version", version=f'linkwatch v{version("linkwatch")}')

	sub = parser.add_subparsers(dest="command")

	p_status = sub.add_parser("status", help="Show the latest ping results", description="Shows the single most recent ping result per target (ISP, Nairobi, Europe).")
	p_status.set_defaults(func=cmd_status)

	p_watch = sub.add_parser("watch", help="Live-refreshing status view",  description="Continuously refreshes the status table in place until interrupted with Ctrl+C.")
	p_watch.add_argument("--interval", type=int, default=5, help="Refresh interval in seconds")
	p_watch.set_defaults(func=cmd_watch)

	p_summary = sub.add_parser("summary", help="Aggregate stats over a time window", description="Shows average, min, and max RTT plus average packet loss per target, over the given window.")
	p_summary.add_argument("--hours", type=int, default=24)
	p_summary.set_defaults(func=cmd_summary)

	p_history = sub.add_parser("history", help="History of pings within a time bucket", description="Get the brakdown of pings within a certain time window")
	p_history.add_argument("--bucket_minutes", type=int, default=60)
	p_history.add_argument("--target", type=str, default="isp")
	p_history.add_argument("--hours", type=int, default=24)
	p_history.set_defaults(func=cmd_history)

	p_outages = sub.add_parser("outages", help="Outages recorded over a time window", description="Lists individual ping results where packet loss met or exceeded the threshold.")
	p_outages.add_argument("--hours", type=int, default=24)
	p_outages.add_argument("--threshold", type=float, default=50.0)
	p_outages.set_defaults(func=cmd_outages)

	args = parser.parse_args()

	if args.command is None:
		parser.print_help()
		sys.exit(0)

	args.func(args)

if __name__ == "__main__":
	main()
