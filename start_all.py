import subprocess
import sys
import time
import os

services = [
    ("Hotel Service", "mcp_servers/hotel_server.py"),
    ("Flight Service", "mcp_servers/flight_server.py"),
    ("Place Service", "mcp_servers/place_server.py"),
    ("Weather Service", "mcp_servers/weather_server.py"),
    ("FastAPI Backend", "main.py"),
]

processes = []


def main():
    print("Starting all TripWeaver services...")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd() + os.pathsep + env.get("PYTHONPATH", "")

    for name, path in services:
        print(f"Launching {name} ({path})...")
        p = subprocess.Popen(
            [sys.executable, path],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        processes.append((name, p))
        time.sleep(1)

    print("\nAll services launched! Visit http://localhost:8000")
    print("Press Ctrl+C to terminate all services.\n")
    try:
        while True:
            for name, p in processes:
                ret = p.poll()
                if ret is not None:
                    print(f"ERROR: {name} terminated with code {ret}")
                    out, _ = p.communicate()
                    print(out)
                    raise KeyboardInterrupt
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTerminating all services...")
        for name, p in processes:
            p.terminate()
            p.wait()
        print("All services terminated.")


if __name__ == "__main__":
    main()
