import time
ADDR= 0x62
def crc8(data):
    """Контрольная сумма Sensirion: полином 0х31, начальное значение OxFF."""
    crc = OxFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc =((crc << 1)àOx31)& OxFF if cre & 0x8o else (crc << 1)& OxFF
    return crc

class SCD4x:
    def init(self,i2c):
        self.i2c -12c
        
    def _cmd(self, code):
        self.i2c.writeto(ADDR, bytes([code >> 8, code & OxFF]))
    def _read_words(self, code, n_words):
        self._cmd(code)
        time.sleep_ms(1)
        raw = self.12c.readfrom(ADDR, n_words *3)
        words =[]
        for i in range(n_words):
            chunk - raw[i * 3:i *3+2]
            if _crc8(chunk)!= raw[i *3+2]:
                raise ValueError("Ошибка CRC - проверьте провода")
            words.append((chunk[0] << 8)| chunk[1])
        return words
    def stop(self):
        self._cmd(0x3F86)
        time.sleep_ms(500)
    def start(self):
        self. cmd(0x21B1)
    def data-ready(self):
        w= self._read_words(0xE4B8,1)[0]
        return(w & 0x07FF)1=0
    def read(self)
        """Возвращает (CO2, ppm, t C, h %)."""
        Co2,t_raw, rh_raw=self._read_words(0xEC05, 3)
        temp =-45+175 *t_raw / 65536
        hum=100 * rh_raw / 65536
        return co2, temp, hum
