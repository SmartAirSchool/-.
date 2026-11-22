# main.py — версия с дисплеем и звуковым сигналом
# ESP32 + SCD40 + TFT 1.8" (ST7735) + активный зуммер, MicroPython.
# Сохраните этот файл на плату под именем main.py (вместо простой версии).
from machine import I2C, SPI, Pin
import time
from scd4x import SCD4x

# ------------------- НАСТРОЙКИ -------------------
INTERVAL_S = 10          # как часто сохранять замер, сек
FILE_NAME = "data.csv"

CO2_WARN = 800           # «скоро проветривать» — рабочее значение, замените своим
CO2_ALARM = 1000         # «проветрите!» — рабочее значение, замените своим
HYST = 50                # тревога снимается, только когда CO2 < CO2_ALARM - HYST

USE_DISPLAY = True
USE_BUZZER = True        # False — «тихий режим» для уроков
BUZZER_ACTIVE_LOW = False # True, если зуммер пищит при сигнале 0
REPEAT_ALARM_S = 300     # повторять сигнал каждые 5 минут, пока CO2 высокий

# Настройки экрана (см. шаг 10.4, если цвета или края неправильные)
TFT_BGR = True
TFT_X_OFFSET = 0
TFT_Y_OFFSET = 0

# Пины
PIN_SDA, PIN_SCL = 21, 22                             # датчик SCD40
PIN_SCK, PIN_MOSI, PIN_CS, PIN_DC, PIN_RST = 18, 23, 5, 17, 16  # экран
PIN_BUZZER = 25

# ------------------- ИНИЦИАЛИЗАЦИЯ -------------------
# Экран создаём первым: ему нужен один большой кусок памяти (40 КБ)
tft = None
if USE_DISPLAY:
    try:
        import st7735
        spi = SPI(2, baudrate=10_000_000, polarity=0, phase=0,
                  sck=Pin(PIN_SCK), mosi=Pin(PIN_MOSI))
        tft = st7735.ST7735(spi, cs=Pin(PIN_CS), dc=Pin(PIN_DC), rst=Pin(PIN_RST), bgr=TFT_BGR,
                            x_offset=TFT_X_OFFSET, y_offset=TFT_Y_OFFSET)
        tft.fill(st7735.BLACK)
        tft.center_text("CO2 MONITOR", 50, st7735.WHITE)
        tft.center_text("progrev...", 70, st7735.GREY)
        tft.show()
    except Exception as e:
        print("# экран не запущен, продолжаю без него:", e)
        tft = None

buzzer = None
if USE_BUZZER:
    buzzer = Pin(PIN_BUZZER, Pin.OUT, value=1 if BUZZER_ACTIVE_LOW else 0)

def beep(times=3, on_ms=150, off_ms=150):
    if buzzer is None:
        return
    on, off = (0, 1) if BUZZER_ACTIVE_LOW else (1, 0)
    for _ in range(times):
        buzzer.value(on); time.sleep_ms(on_ms)
        buzzer.value(off); time.sleep_ms(off_ms)

def get_level(co2, prev_level):
    """0 - норма, 1 - скоро проветривать, 2 - проветрите. (с гистерезисом)"""
    if co2 >= CO2_ALARM:
        return 2
    if prev_level == 2 and co2 >= CO2_ALARM - HYST:
        return 2               # не дёргаем тревогу на границе
    if co2 >= CO2_WARN:
        return 1
    return 0

def draw(co2, temp, hum, level, t):
    if tft is None:
        return
    import st7735 as s
    bg = (s.GREEN, s.YELLOW, s.RED)[level]
    fg = s.WHITE if level == 2 else s.BLACK
    status = ("NORMA", "SKORO PROVETRIT", "PROVETRITE!")[level]
    tft.fill(s.BLACK)
    tft.fill_rect(0, 0, 128, 80, bg)             # цветная «шапка»
    tft.center_text("CO2, ppm", 6, fg)
    num = str(co2)
    tft.center_text(num, 22, fg, 4 if len(num) <= 4 else 3)  # крупная цифра
    tft.center_text(status, 64, fg)
    tft.big_text("T", 4, 90, s.GREY, 2)
    tft.big_text("{:.1f}C".format(temp), 28, 90, s.WHITE, 2)
    tft.big_text("H", 4, 114, s.GREY, 2)
    tft.big_text("{:.0f}%".format(hum), 28, 114, s.WHITE, 2)
    tft.center_text("t = {} s".format(t), 146, s.GREY)
    tft.show()

# ------------------- ЗАПУСК -------------------
i2c = I2C(0, scl=Pin(PIN_SCL), sda=Pin(PIN_SDA), freq=100000)
sensor = SCD4x(i2c)
sensor.stop()
sensor.start()
print("Датчик запущен, первые данные через ~5 секунд")

try:
    open(FILE_NAME).close()
except OSError:
    with open(FILE_NAME, "w") as f:
        f.write("time_s,CO2_ppm,Temp_C,Humidity_percent\n")

start_ms = time.ticks_ms()
level = 0
last_alarm_s = -REPEAT_ALARM_S

while True:
    try:
        if sensor.data_ready():
            co2, temp, hum = sensor.read()
            t = time.ticks_diff(time.ticks_ms(), start_ms) // 1000
            line = "{},{},{:.2f},{:.2f}".format(t, co2, temp, hum)
            print(line)
            with open(FILE_NAME, "a") as f:        # запись — главное, она идёт первой
                f.write(line + "\n")

            new_level = get_level(co2, level)
            try:
                draw(co2, temp, hum, new_level, t)
            except Exception as e:
                print("# ошибка экрана:", e)

            if new_level == 2 and (level < 2 or t - last_alarm_s >= REPEAT_ALARM_S):
                beep(3)                            # вошли в тревогу или пора напомнить
                last_alarm_s = t
            level = new_level
        else:
            print("# данные ещё не готовы")
    except Exception as e:
        print("# ошибка чтения:", e)
    time.sleep(INTERVAL_S)
