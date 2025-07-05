import time
import board
import displayio
import terminalio

from kmk.kmk_keyboard import KMKKeyboard
from kmk.scanners import DiodeOrientation
from kmk.keys import KC
from kmk.modules.layers import Layers
from kmk.extensions.encoder import EncoderHandler
from kmk.extensions.OLED_SSD1306 import OLED
from kmk.kmk_module import KMKModule

#kmk setup
kbd = KMKKeyboard()
kbd.row_pins = (board.D0, board.D1, board.D2)
kbd.col_pins = (board.D11, board.D10, board.D9, board.D8)
kbd.diode_orientation = DiodeOrientation.COL2ROW

#encoder
encoder_ext = EncoderHandler(encoders=((board.D4, board.D7, None),), div=1)
kbd.extensions.append(encoder_ext)

#OLED config 
displayio.release_displays()
oled_ext = OLED(
    i2c          = board.I2C(),
    width        = 128,
    height       = 32,
    line_spacing = 1,
    font         = terminalio.FONT,
    to_display   = lambda kb: kb.oled_message
)
kbd.extensions.append(oled_ext)
kbd.oled_message = ''

#modes
SC, TP = 0, 1
kbd.modules.append(Layers())

keymap_shortcuts = [
    KC.LCTL(KC.C),
    KC.LCTL(KC.V),
    KC.LCTL(KC.X),
    KC.LCTL(KC.Z),
    KC.LCTL(KC.Y),
    KC.LCTL(KC.A),
    KC.LCTL(KC.TAB),
    KC.LCTL(KC.LSFT(KC.TAB)),
    KC.LALT(KC.F4),
    KC.LCTL(KC.LEFT),
    KC.LCTL(KC.RIGHT),
    KC.TO(TP),
]

keymap_typing = [
    KC.NO, KC.NO, KC.NO, KC.NO,
    KC.NO, KC.NO, KC.NO, KC.NO,
    KC.NO, KC.NO, KC.ENTER, KC.TO(SC),
]
kbd.keymap = [keymap_shortcuts, keymap_typing]

#brightness control module
class Brightness(KMKModule):
    def __init__(self, oled):
        self.oled = oled
        self._brightness = 1.0  # 0‑1
    def after_encoder(self, keyboard):
        pos = keyboard.encoders[0].position
        delta = pos - getattr(self, '_last_pos', pos)
        if delta:
            self._brightness = max(0, min(1, self._brightness + 0.1*(1 if delta>0 else -1)))
            self.oled.display.brightness = self._brightness
            keyboard.oled_message = f"Brightness: {int(self._brightness*100):3d}%"
        self._last_pos = pos
kbd.modules.append(Brightness(oled_ext))

#t9 style typing module
class T9(KMKModule):
    TAP_DELAY = 0.5
    MAX_CHARS = 21

    _map = {
        0: "1./",
        1: "2ABC",
        2: "3DEF",
        4: "4GHI",
        5: "5JKL",
        6: "6MNO",
        8: "7PQRS",
        9: "8TUV",
        10: "9WXYZ",
        3: "0 /",
    }

    def __init__(self):
        self.buffer = ''
        self.last_key = None
        self.last_time = 0
        self.tap_index = 0
        self._pending_char = None

    def process_key(self, keyboard, key, is_pressed, first_time):
        layer = keyboard.active_layers[0]
        if layer != TP or not is_pressed or not first_time:
            return True

        now = time.monotonic()

        #confirm current char
        if key == 7:
            if self._pending_char:
                self.buffer += self._pending_char
                keyboard.oled_message = self._trim(self.buffer.replace('\n', '/'))
                self._pending_char = None
                self.last_key = None
                self.tap_index = 0
            return False

        #switch mode
        if key == 11:
            keyboard.set_layer(TP)
            keyboard.oled_message = 'Typing Mode'
            return False

        if key in self._map:
            if self.last_key == key and (now - self.last_time) < self.TAP_DELAY:
                self.tap_index = (self.tap_index + 1) % len(self._map[key])
                keyboard.tap_key(KC.BSPC)
            else:
                self.tap_index = 0

            char = self._map[key][self.tap_index]
            if char == '/':
                keyboard.tap_key(KC.ENTER)
                char = '\n'
            else:
                keyboard.send_string(char)

            self._pending_char = char
            self.last_key = key
            self.last_time = now

            display_text = self.buffer + (char if char != '\n' else '/')
            keyboard.oled_message = self._trim(display_text)
            return False

        return True

    def _trim(self, txt):
        return txt[-self.MAX_CHARS:]

kbd.modules.append(T9())

if __name__ == '__main__':
    kbd.go()