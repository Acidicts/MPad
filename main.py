import time
import serial
import serial.tools.list_ports
import yfinance as yf

TICKER = "RR.L"          # Rolls-Royce Holdings (LSE, priced in pence)
INTERVAL = 30            # seconds between sends (pad goes STALE after 180)
VID, PID = 0x2886, 0x42  # Seeeduino XIAO RP2040 running CircuitPython
EXPECTED_PORTS = 2       # console + data


def find_pad_ports():
    return sorted(
        p.device
        for p in serial.tools.list_ports.comports()
        if p.vid == VID and p.pid == PID
    )


def open_ports(devices):
    opened = []
    for dev in devices:
        try:
            opened.append(serial.Serial(dev, 115200, timeout=1, write_timeout=2))
        except (serial.SerialException, OSError) as e:
            print(f"Could not open {dev}: {e}", flush=True)
    return opened


def close_all(ports):
    for p in ports:
        try:
            p.close()
        except Exception:
            pass


def get_quote(ticker):
    info = ticker.fast_info
    price = float(info["last_price"])
    prev = float(info["previous_close"])
    change = (price - prev) / prev * 100
    return price, change


def main():
    ticker = yf.Ticker(TICKER)
    ports = []
    last_quote = None      # (price, change), reused if Yahoo fails
    last_sent = 0
    last_fetch = 0

    while True:
        # If the pad's port set changed (unplug, re-enumeration), reconnect
        current = find_pad_ports()
        connected = sorted(p.port for p in ports)
        if ports and current != connected:
            print("Port set changed, reconnecting...", flush=True)
            close_all(ports)
            ports = []

        if not ports:
            if len(current) < EXPECTED_PORTS:
                print(f"Waiting for pad ({len(current)}/{EXPECTED_PORTS} ports)...", flush=True)
                time.sleep(3)
                continue
            ports = open_ports(current)
            if len(ports) < EXPECTED_PORTS:
                close_all(ports)
                ports = []
                time.sleep(3)
                continue
            print("Connected:", [p.port for p in ports], flush=True)
            last_sent = 0  # send immediately

        now = time.time()

        # Refresh the quote every 60s (don't hammer Yahoo)
        if now - last_fetch >= 60:
            try:
                last_quote = get_quote(ticker)
                last_fetch = now
            except Exception as e:
                print("Fetch failed:", e, flush=True)
                last_fetch = now - 50  # retry in ~10s

        # Send the latest known quote every INTERVAL seconds
        if last_quote and now - last_sent >= INTERVAL:
            price, change = last_quote
            msg = f"{TICKER},{price:.2f},{change:+.2f}\n".encode()
            try:
                for p in ports:
                    p.write(msg)
                    p.flush()
                print(f"Sent: {price:.2f}p ({change:+.2f}%)", flush=True)
                last_sent = now
            except (serial.SerialException, OSError):
                print("Write failed, reconnecting...", flush=True)
                close_all(ports)
                ports = []
                continue

        time.sleep(1)


if __name__ == "__main__":
    main()