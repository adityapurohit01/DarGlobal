"""Automated keep-alive pinger for Render-hosted DarGlobal Concierge.

Pings the live application every 9 minutes to keep the Render container
permanently active and warm (Render free-tier spins down after 15 minutes).
"""

import logging
import time
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
TARGET_URL = "https://darglobal-concierge-6udw.onrender.com/"
INTERVAL_SECONDS = 540  # 9 minutes


def ping_container() -> bool:
    """Sends a lightweight GET request to keep the container awake."""
    logging.info(f"Pinging {TARGET_URL}...")
    try:
        req = urllib.request.Request(
            TARGET_URL,
            headers={"User-Agent": "DarGlobal-KeepAlive/1.0 (Container Warmup)"},
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            logging.info(f"Container awake! HTTP status: {resp.status}")
            return True
    except Exception as e:
        logging.warning(f"Ping notice: {e}")
        return False


def run_loop():
    logging.info("DarGlobal Keep-Alive Daemon started. Press Ctrl+C to terminate.")
    while True:
        ping_container()
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    run_loop()
