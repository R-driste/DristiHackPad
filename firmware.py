'''
Firmware for the macropad with CircuitPython, supporting shortcuts and dial typing
'''

import board
import keypad
import usb_hid
import time
import displayio
import terminalio
import digitalio
import rotaryio

from adafruit_display_text import label
from adafruit_displayio_ssd1306 import SSD1306_I2C
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

#OLED Setup
displayio.release_displays()  #reset screen
i2c = board.I2C()  #setup i2c w scl sda pins
display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
display = SSD1306_I2C(128, 32, display_bus)
splash = displayio.Group()  #container for stuff to display
display.show(splash)

modes = ["Shortcuts", "Typing"] #modes for macropad
mode = 0

text_area = label.Label(terminalio.FONT, text="", x=0, y=12) #text for updating
splash.append(text_area)

MAX_CHARS = 21 #max characters for OLED

def show_mode(text=None):
    if text is None:
        text = f"Mode: {modes[mode]}"
    if len(text) > MAX_CHARS:
        text = text[-MAX_CHARS:] #truncate long text
    text_area.text = text
    display.refresh()

show_mode() #show initial mode

#key matrix setup
rows = (board.D0, board.D1, board.D2)
cols = (board.D11, board.D10, board.D9, board.D8)
keys = keypad.KeyMatrix(row_pins=rows, column_pins=cols, columns_to_anodes=False)
kbd = Keyboard(usb_hid.devices)

#rotary encoder setup
encoder = rotaryio.IncrementalEncoder(board.D4, board.D7)
last_position = encoder.position

#shortcut mapping keys
shortcut_map = {
    0: (Keycode.CONTROL, Keycode.C), #Copy
    1: (Keycode.CONTROL, Keycode.V), #Paste
    2: (Keycode.CONTROL, Keycode.X), #Cut
    3: (Keycode.CONTROL, Keycode.Z), #Undo
    4: (Keycode.CONTROL, Keycode.Y), #Redo
    5: (Keycode.CONTROL, Keycode.A), #Select all
    6: (Keycode.CONTROL, Keycode.TAB), #Previous tab
    7: (Keycode.CONTROL, Keycode.SHIFT, Keycode.TAB), #Next tab,
    8: (Keycode.ALT, Keycode.F4), #Close window,
    9: (Keycode.CONTROL, Keycode.LEFT_ARROW),  #Cursor left
    10: (Keycode.CONTROL, Keycode.RIGHT_ARROW), #Cursor right
}

# mapping
t9_map = {
    0: "1", 1: "2ABC", 2: "3DEF",
    3: "4GHI", 4: "5JKL", 5: "6MNO",
    6: "7PQRS", 7: "8TUV", 8: "9WXYZ",
    9: "0 "
}

buffer = "" #typed so far
last_tap_time = 0 #keep delay in typing
TAP_DELAY = 0.5
last_key = None #track last pressed
tap_index = 0

while True:
    event = keys.events.get()
    if event:
        key_num = event.key_number

        #switch the mode when 11 gets pressed
        if key_num == 11 and event.pressed:
            mode = (mode + 1) % len(modes)
            buffer = ""
            show_mode()
            continue
        
        #typing mode
        if mode == 1:
            if event.pressed:
                if key_num == 10:  #enter
                    kbd.press(Keycode.ENTER)
                    kbd.release(Keycode.ENTER)
                    buffer += "/"  #separate newline
                    show_mode(buffer)

                elif key_num in t9_map:
                    now = time.monotonic()
                    if last_key == key_num and now - last_tap_time < TAP_DELAY:
                        tap_index = (tap_index + 1) % len(t9_map[key_num])
                    else:
                        tap_index = 0
                    letter = t9_map[key_num][tap_index]
                    last_tap_time = now
                    last_key = key_num

                    if buffer and last_key == key_num:
                        buffer = buffer[:-1] + letter
                    else:
                        buffer += letter
                    show_mode(buffer)

        #shortcut mode
        elif mode == 0:
            if event.pressed and key_num in shortcut_map:
                combo = shortcut_map[key_num]
                for k in combo:
                    kbd.press(k)
            elif event.released and key_num in shortcut_map:
                combo = shortcut_map[key_num]
                for k in combo:
                    kbd.release(k)

    #rotary encoder position update
    pos = encoder.position
    if pos != last_position:
        if pos > last_position:
            kbd.press(Keycode.RIGHT_ARROW)
            kbd.release(Keycode.RIGHT_ARROW)
        else:
            kbd.press(Keycode.LEFT_ARROW)
            kbd.release(Keycode.LEFT_ARROW)
        last_position = pos

    time.sleep(0.01)
