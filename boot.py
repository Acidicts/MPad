# boot.py
import usb_cdc
import storage
import board
import digitalio

# --- Enable the second USB serial port for the PC stock script ---
usb_cdc.enable(console=True, data=True)

# --- Optional: hide the CIRCUITPY drive during normal use ---
# Hold the first key (D0) while plugging in to keep the drive visible for editing.
# Without this held, the drive is hidden and the pad behaves like a plain keyboard.
button = digitalio.DigitalInOut(board.D0)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

if button.value:  # not held (pull-up: True means not pressed)
    storage.disable_usb_drive()
    # storage.remount("/", readonly=False)  # uncomment if main.py needs to write files

button.deinit()