import board
import digitalio
import bitbangio
import time
import usb_cdc
import adafruit_ssd1306

from kmk.kmk_keyboard import KMKKeyboard
from kmk.scanners.keypad import KeysScanner
from kmk.extensions.RGB import RGB, AnimationModes
from kmk.extensions.media_keys import MediaKeys
from kmk.modules import Module
from kmk.modules.encoder import EncoderHandler
from kmk.keys import KC

# ---------------- Pins ----------------
ROTA = board.D10
ROTB = board.D9
RS_Switch1 = board.D8      # encoder push button
RS_Switch2 = board.D7      # used as ground for the encoder button
NEOPIXEL = board.D5
PINS = [board.D0, board.D1, board.D2]

# D7 acts as a ground pin for the encoder button
encoder_gnd = digitalio.DigitalInOut(RS_Switch2)
encoder_gnd.direction = digitalio.Direction.OUTPUT
encoder_gnd.value = False

# ---------------- OLED (128x32) ----------------
i2c = bitbangio.I2C(scl=board.D4, sda=board.D3)
oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, addr=0x3C)

# 5x7 digit glyphs (each row is 5 bits, top to bottom) for the big price
GLYPHS = {
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F),
    "3": (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    ".": (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C),
    "-": (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),
}


class StockDisplay(Module):
    """Stock ticker with arrow, big price and sparkline.

    Message format (one per line): SYMBOL,PRICE,CHANGE_PCT
    Example: RR.L,512.40,+1.35
    """

    STALE_AFTER = 180      # seconds without data before showing STALE
    MAX_BUF = 256
    HISTORY = 40           # number of points kept for the sparkline

    def __init__(self, oled):
        self.oled = oled
        self.buf = b""
        self.symbol = "RR.L"
        self.price = None        # float
        self.change = 0.0        # float, percent
        self.history = []
        self.dirty = True
        self.stale = False
        self.last_rx = None

    # ---------- drawing helpers ----------
    def _text_big(self, text, x, y, scale=2):
        """Draw digits scaled up using the GLYPHS bitmaps (no framebuf needed)."""
        o = self.oled
        cx = x
        for ch in text:
            glyph = GLYPHS.get(ch)
            if glyph is None:
                cx += 6 * scale
                continue
            for row, bits in enumerate(glyph):
                for col in range(5):
                    if bits & (0x10 >> col):
                        o.fill_rect(cx + col * scale, y + row * scale, scale, scale, 1)
            cx += 6 * scale

    def _arrow(self, x, y, direction):
        """9x5 filled triangle. direction: 1 up, -1 down, 0 flat."""
        o = self.oled
        if direction > 0:
            for i in range(5):
                o.hline(x + 4 - i, y + i, 1 + i * 2, 1)
        elif direction < 0:
            for i in range(5):
                o.hline(x + i, y + i, 9 - i * 2, 1)
        else:
            o.fill_rect(x, y + 2, 9, 2, 1)

    def _sparkline(self, x, y, w, h):
        pts = self.history[-w:]
        if len(pts) < 2:
            return
        lo, hi = min(pts), max(pts)
        rng = (hi - lo) or 1.0
        prev = None
        for i, v in enumerate(pts):
            py = y + h - 1 - int((v - lo) / rng * (h - 1))
            px = x + i * (w - 1) // (len(pts) - 1)
            if prev is not None:
                self.oled.line(prev[0], prev[1], px, py, 1)
            prev = (px, py)

    def _draw(self):
        o = self.oled
        o.fill(0)

        if self.price is None:
            o.text("RR.L", 0, 0, 1)
            o.text("Waiting for data", 0, 16, 1)
            o.show()
            return

        direction = 1 if self.change > 0 else (-1 if self.change < 0 else 0)

        # Top row: ticker, arrow, change %
        o.text(self.symbol, 0, 0, 1)
        self._arrow(48, 0, direction)
        o.text("{:+.2f}%".format(self.change), 62, 0, 1)

        # Big price on the left (2x glyphs are 12px per char, 14px tall)
        self._text_big("{:.1f}".format(self.price), 0, 14, 2)

        # Sparkline in the bottom-right corner
        self._sparkline(88, 14, 40, 16)

        if self.stale:
            o.fill_rect(0, 24, 40, 8, 1)
            o.text("STALE", 2, 24, 0)

        o.show()

    # ---------- data handling ----------
    def _parse(self, line):
        try:
            parts = line.decode().strip().split(",")
            if len(parts) != 3:
                return
            symbol, price, change = parts
            self.symbol = symbol
            self.price = float(price)
            self.change = float(change)
            self.history.append(self.price)
            if len(self.history) > self.HISTORY:
                self.history.pop(0)
            self.stale = False
            self.last_rx = time.monotonic()
            self.dirty = True
        except Exception:
            pass

    def during_bootup(self, keyboard):
        try:
            self._draw()
        except Exception:
            pass

    def before_matrix_scan(self, keyboard):
        port = usb_cdc.data
        if port is not None and port.in_waiting:
            self.buf += port.read(port.in_waiting)
            if len(self.buf) > self.MAX_BUF and b"\n" not in self.buf:
                self.buf = b""
            while b"\n" in self.buf:
                line, self.buf = self.buf.split(b"\n", 1)
                self._parse(line)

        if (
            self.last_rx is not None
            and not self.stale
            and time.monotonic() - self.last_rx > self.STALE_AFTER
        ):
            self.stale = True
            self.dirty = True

        if self.dirty:
            self.dirty = False
            try:
                self._draw()
            except Exception:
                pass

    def after_matrix_scan(self, keyboard): pass
    def process_key(self, keyboard, key, is_pressed, int_coord): return key
    def before_hid_send(self, keyboard): pass
    def after_hid_send(self, keyboard): pass
    def on_powersave_enable(self, keyboard): pass
    def on_powersave_disable(self, keyboard): pass


# ---------------- Keyboard ----------------
keyboard = KMKKeyboard()
keyboard.modules.append(StockDisplay(oled))

rgb_ext = RGB(
    pixel_pin=NEOPIXEL,
    num_pixels=3,
    hue_default=100,
    sat_default=255,
    val_default=15,
    val_limit=25,
    animation_speed=1,
    animation_mode=AnimationModes.RAINBOW,
    refresh_rate=30,
)
keyboard.extensions.append(rgb_ext)
keyboard.extensions.append(MediaKeys())

keyboard.matrix = KeysScanner(pins=PINS, value_when_pressed=False)

# Encoder: rotation on D10/D9, push button on D8 (grounded via D7)
encoder_handler = EncoderHandler()
keyboard.modules.append(encoder_handler)
encoder_handler.pins = ((ROTA, ROTB, RS_Switch1, False),)
encoder_handler.map = (((KC.VOLU, KC.VOLD, KC.MUTE),),)

keyboard.keymap = [[KC.MPRV, KC.MPLY, KC.MNXT]]

if __name__ == '__main__':
    keyboard.go()