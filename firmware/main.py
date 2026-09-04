# You import all the IOs of your board
import board

# These are imports from the kmk library
from kmk.kmk_keyboard import KMKKeyboard
from kmk.scanners.keypad import KeysScanner
from kmk.extensions.RGB import RGB, AnimationModes
from kmk.extensions.media_keys import MediaKeys
from kmk.modules.macros import Macros
from kmk.modules.encoder import EncoderHandler
from kmk.keys import KC

# Pin definitions based on your schematic
ROTA = board.D10         # RS_A
ROTB = board.D9          # RS_B
RS_Switch1 = board.D8    # Push Button Pin 1
RS_Switch2 = board.D7    # Push Button Pin 2

NEOPIXEL = board.D5

# This is the main instance of your keyboard
keyboard = KMKKeyboard()

# Add the macro extension
macros = Macros()
keyboard.modules.append(macros)

# Define your matrix pins here (Switch_1, Switch_2, Switch_3)
PINS = [board.D0, board.D1, board.D2]

# RGB LEDs settings
rgb_ext = RGB( 
    pixel_pin = NEOPIXEL,
    num_pixels = 3,
    hue_default = 100,
    sat_default = 255,
    val_default = 15,
    val_limit = 25,
    animation_speed = 1,
    animation_mode = AnimationModes.RAINBOW,
    refresh_rate = 30,
)
keyboard.extensions.append(rgb_ext)
keyboard.extensions.append(MediaKeys())

# Tell kmk we are not using a key matrix for the switches
keyboard.matrix = KeysScanner(
    pins = PINS,
    value_when_pressed = False,
)

# Encoder settings using RS_Switch1 (D8) and RS_Switch2 (D7) from your schematic
encoder_handler = EncoderHandler()
keyboard.modules.append(encoder_handler)
encoder_handler.pins = ((board.D8, board.D7, None, False),)
encoder_handler.map = (((KC.VOLD, KC.VOLU, KC.MUTE),),)

# Here you define the buttons corresponding to the pins
keyboard.keymap = [
    [KC.MPRV, KC.MPLY, KC.MNXT]
]

# Start kmk!
if __name__ == '__main__':
    keyboard.go()