from flask import Flask, jsonify, render_template
import subprocess
import re
import statistics

app = Flask(__name__, template_folder="../frontend")

TARGET = "google.com"
PING_COUNT = 5


def get_wifi_status():
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return {"connected": False, "ssid": None, "signal": None}

    if result.returncode != 0:
        return {"connected": False, "ssid": None, "signal": None}

    def field(pattern):
        match = re.search(pattern, result.stdout, re.MULTILINE | re.IGNORECASE)
        return match.group(1).strip() if match else None

    ssid = field(r"^\s*SSID\s*:\s*(.+?)\s*$")
    state = field(r"^\s*State\s*:\s*(.+?)\s*$")
    signal = field(r"^\s*Signal\s*:\s*(\d+)%")
    band = field(r"^\s*Band\s*:\s*(.+?)\s*$")
    receive = field(r"^\s*Receive rate \(Mbps\)\s*:\s*([\d.]+)")
    transmit = field(r"^\s*Transmit rate \(Mbps\)\s*:\s*([\d.]+)")

    connected = bool(ssid) and state is not None and state.lower() == "connected"

    return {
        "connected": connected,
        "ssid": ssid,
        "signal": int(signal) if signal else None,
        "band": band,
        "receive_mbps": float(receive) if receive else None,
        "transmit_mbps": float(transmit) if transmit else None,
    }


def run_latency_test():
    results = []

    for i in range(PING_COUNT):
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "1000", TARGET],
            capture_output=True,
            text=True,
        )

        # Parse "time=XXms" or "time<1ms" out of Windows ping output
        match = re.search(r"time[=<](\d+)ms", result.stdout)
        if match:
            results.append(float(match.group(1)))

    if not results:
        return {
            "success": False,
            "message": "No response received",
        }

    avg_latency = sum(results) / len(results)
    jitter = statistics.pstdev(results) if len(results) > 1 else 0.0

    is_stable = jitter < 20

    return {
        "success": True,
        "target": TARGET,
        "count": len(results),
        "pings_ms": [round(r, 2) for r in results],
        "average_ms": round(avg_latency, 2),
        "jitter_ms": round(jitter, 2),
        "stable": is_stable,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/scan")
def scan():
    data = run_latency_test()
    return jsonify(data)


@app.route("/network")
def network():
    return jsonify(get_wifi_status())


if __name__ == "__main__":
    app.run(debug=True)