# st7735.py - минимальный драйвер цветного TFT 1.8" 128x160 (контроллер ST7735 / ST7735S)
# для MicroPython на ESP32. Рисование идет в буфер в памяти, на экран - командой show().
import framebuf
import time
from machine import Pin

WIDTH = 128
HEIGHT = 160

def color565(r, g, b):
    """Цвет RGB (0-255) -> формат экрана RGB565.
    Байты переставлены местами: ST7735 ждет старший байт первым."""
    c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return ((c & 0xFF) << 8) | (c >> 8)

BLACK = color565(0, 0, 0)
WHITE = color565(255, 255, 255)
RED = color565(220, 30, 30)
GREEN = color565(30, 170, 60)
YELLOW = color565(250, 200, 0)
BLUE = color565(30, 90, 220)
GREY = color565(140, 140, 140)

# Стандартная последовательность настроек ST7735 (питание, частота кадров, гамма)
_INIT = (
    (0xB1, b"\x01\x2C\x2D"),                          # FRMCTR1
    (0xB2, b"\x01\x2C\x2D"),                          # FRMCTR2
    (0xB3, b"\x01\x2C\x2D\x01\x2C\x2D"),              # FRMCTR3
    (0xB4, b"\x07"),                                  # INVCTR
    (0xC0, b"\xA2\x02\x84"),                          # PWCTR1
    (0xC1, b"\xC5"),                                  # PWCTR2
    (0xC2, b"\x0A\x00"),                              # PWCTR3
    (0xC3, b"\x8A\x2A"),                              # PWCTR4
    (0xC4, b"\x8A\xEE"),                              # PWCTR5
    (0xC5, b"\x0E"),                                  # VMCTR1
    (0x20, None),                                     # INVOFF - без инверсии цветов
    (0x3A, b"\x05"),                                  # COLMOD - 16 бит на точку
    (0xE0, b"\x02\x1C\x07\x12\x37\x32\x29\x2D\x29\x25\x2B\x39\x00\x01\x03\x10"),
    (0xE1, b"\x03\x1D\x07\x06\x2E\x2C\x29\x2D\x2E\x2E\x37\x3F\x00\x00\x02\x10"),
)

class ST7735(framebuf.FrameBuffer):
    def __init__(self, spi, cs, dc, rst, bgr=True, x_offset=0, y_offset=0):
        self.spi = spi
        self.cs = Pin(cs, Pin.OUT, value=1)
        self.dc = Pin(dc, Pin.OUT, value=0)
        self.rst = Pin(rst, Pin.OUT, value=1)
        self.width = WIDTH
        self.height = HEIGHT
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.buffer = bytearray(WIDTH * HEIGHT * 2)       # 40 КБ - весь экран
        super().__init__(self.buffer, WIDTH, HEIGHT, framebuf.RGB565)
        self.init(bgr)

    def _write(self, cmd, data=None):
        self.cs(0)
        self.dc(0)
        self.spi.write(bytes([cmd]))                      # A0 = 0 - команда
        if data is not None:
            self.dc(1)
            self.spi.write(data)                          # A0 = 1 - данные
        self.cs(1)

    def init(self, bgr):
        self.rst(1); time.sleep_ms(5)                     # аппаратный сброс
        self.rst(0); time.sleep_ms(20)
        self.rst(1); time.sleep_ms(150)
        self._write(0x01); time.sleep_ms(150)             # SWRESET
        self._write(0x11); time.sleep_ms(255)             # SLPOUT - выход из сна
        for cmd, data in _INIT:
            self._write(cmd, data)
        # MADCTL: ориентация «портрет» и порядок цветов (BGR или RGB)
        self._write(0x36, bytes([0xC8 if bgr else 0xC0]))
        self._write(0x13); time.sleep_ms(10)              # NORON
        self._write(0x29); time.sleep_ms(100)             # DISPON - включить экран
        self.fill(BLACK)
        self.show()

    def show(self):
        """Переносит буфер из памяти на экран."""
        x0, y0 = self.x_offset, self.y_offset
        x1, y1 = x0 + WIDTH - 1, y0 + HEIGHT - 1
        self._write(0x2A, bytes([0, x0, 0, x1]))          # столбцы
        self._write(0x2B, bytes([0, y0, 0, y1]))          # строки
        self._write(0x2C, self.buffer)                    # запись пикселей

    def big_text(self, s, x, y, color, scale=2):
        """Текст встроенным шрифтом 8x8, увеличенный в scale раз.
        Шрифт содержит только латиницу, цифры и знаки."""
        w = 8 * len(s)
        buf = bytearray(((w + 7) // 8) * 8)
        mono = framebuf.FrameBuffer(buf, w, 8, framebuf.MONO_HLSB)
        mono.text(s, 0, 0, 1)
        for j in range(8):
            for i in range(w):
                if mono.pixel(i, j):
                    self.fill_rect(x + i * scale, y + j * scale, scale, scale, color)

    def center_text(self, s, y, color, scale=1):
        """Текст по центру экрана по горизонтали."""
        x = (WIDTH - 8 * len(s) * scale) // 2
        if scale == 1:
            self.text(s, x, y, color)
        else:
            self.big_text(s, x, y, color, scale)
