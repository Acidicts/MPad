import usb_hid
import board
import digitalio
import storage
import supervisor
import time

usb_hid.enable(
    (usb_hid.Device.KEYBOARD,
     usb_hid.Device.CONSUMER_CONTROL)
)

# SW2
switch_2 = board.D1

button = digitalio.DigitalInOut(switch_2)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

# Small delay to let pins stabilize
time.sleep(0.01)

# Read the button
button_pressed = not button.value

# Clean up
switch_2.deinit()

if button_pressed:
    print("SW2 pressed at boot - USB drive enabled, main.py disabled")
    supervisor.disable_autoreload()
else:
    storage.disable_usb_drive()
    print("USB drive disabled - running normally")

supervisor.runtime.serial_bytes_available = button_pressed