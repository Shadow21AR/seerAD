import subprocess

def get_faketime_string(dc_ip: str) -> str:
    """
    Fetches date+time from the first line of `ntpdate -q` output for the given DC IP
    and returns it in a faketime-compatible format: "YYYY-MM-DD HH:MM:SS".
    """
    try:
        output = subprocess.check_output(["ntpdate", "-q", dc_ip], text=True, stderr=subprocess.DEVNULL)
        lines = output.strip().splitlines()

        if not lines:
            print(f"[!] Failed to get time from {dc_ip}")
            return None

        first_line = lines[-1] if "step time server" in lines[-1] else lines[0]
        parts = first_line.strip().split()

        if len(parts) < 3:
            print("[!] Failed to parse date/time from ntpdate output")
            return None

        # e.g., "14 Jul 21:55:39"
        day, month, time_str = parts[0], parts[1], parts[2]
        from datetime import datetime

        now = datetime.now()
        try:
            # Try current year
            parsed = datetime.strptime(f"{day} {month} {now.year} {time_str}", "%d %b %Y %H:%M:%S")
        except ValueError:
            # fallback to alternate month/day format
            print("[!] Failed to parse time format")
            return None

        return parsed.strftime("%Y-%m-%d %H:%M:%S")

    except subprocess.CalledProcessError as e:
        print(f"[!] ntpdate failed: {e}")
        return None