# MicroPython SHTC3 Digital Humidity and Temperature Sensor Driver
# https://github.com/jposada202020/MicroPython_SHTC3
#
# Based on the Arduino SHTC3 Library
# https://github.com/adafruit/Adafruit_SHTC3
#
# Copyright (c) 2020 Jose Miguel Pons
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
`shtc3`
====================================================

MicroPython SHTC3 Digital Humidity and Temperature Sensor Driver

* Author(s): Jose Miguel Pons

Implementation Notes
--------------------

**Hardware:**

* SHTC3 Digital Humidity and Temperature Sensor Breakout:
  https://www.adafruit.com/product/4636

**Software and Dependencies:**

* MicroPython firmware for the board
* The `MicroPython I2C` classes:
  https://docs.micropython.org/en/latest/library/machine.I2C.html

"""

import time
from micropython import const

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/jposada202020/MicroPython_SHTC3.git"

# SHTC3 ADDRESS
_SHTC3_DEFAULT_ADDR = const(0x70)

# SHTC3 COMMANDS
_SHTC3_WAKEUP = const(0x3517)
_SHTC3_SLEEP = const(0xB098)
_SHTC3_SWRESET = const(0x805D)
_SHTC3_READID = const(0xEFC8)

# MEASUREMENT MODES
_SHTC3_MEAS_T_FIRST_LOW_POWER = const(0x609C)
_SHTC3_MEAS_T_FIRST_NORMAL = const(0x7866)
_SHTC3_MEAS_H_FIRST_LOW_POWER = const(0x5C24)
_SHTC3_MEAS_H_FIRST_NORMAL = const(0x7030)


class SHTC3:
    """
    MicroPython SHTC3 Digital Humidity and Temperature Sensor Driver.
    """

    def __init__(self, i2c, address=_SHTC3_DEFAULT_ADDR):
        self._i2c = i2c
        self._address = address
        self._buffer = bytearray(6)
        self._cmd_buffer = bytearray(2)
        self._cached_temperature = None
        self._cached_humidity = None
        self._last_update_time = None
        self.wakeup()
        self.reset()
        self._device_id = self.device_id
        self.sleep()

    @property
    def device_id(self):
        """The device ID"""
        self._write_command(_SHTC3_READID)
        time.sleep_ms(1)
        self._i2c.readfrom_into(self._address, memoryview(self._buffer)[0:3])
        if self._check_crc(self._buffer, 0, 2) != self._buffer[2]:
            raise RuntimeError("CRC check failed for device ID")
        return (self._buffer[0] << 8) | self._buffer[1]

    @property
    def relative_humidity(self):
        """The measured relative humidity in %."""
        self._perform_measurement()
        return self._cached_humidity

    @property
    def temperature(self):
        """The measured temperature in Celsius."""
        self._perform_measurement()
        return self._cached_temperature

    def _perform_measurement(self):
        # Cache measurements to avoid back-to-back I2C query collisions
        if self._last_update_time is not None and time.ticks_diff(time.ticks_ms(), self._last_update_time) < 1000:
            return

        for attempt in range(3):
            self.wakeup()
            self._write_command(_SHTC3_MEAS_T_FIRST_NORMAL)
            time.sleep_ms(15)  # 15ms delay matching the C++ Adafruit_SHTC3 library
            
            try:
                self._i2c.readfrom_into(self._address, self._buffer)
            except OSError:
                pass # Ignore raw I2C bus errors and allow the loop to retry
            self.sleep()
            
            if self._check_crc(self._buffer, 0, 2) == self._buffer[2] and self._check_crc(self._buffer, 3, 5) == self._buffer[5]:
                temp_data = (self._buffer[0] << 8) | self._buffer[1]
                self._cached_temperature = self._calculate_temperature(temp_data)
                humidity_data = (self._buffer[3] << 8) | self._buffer[4]
                self._cached_humidity = self._calculate_humidity(humidity_data)
                self._last_update_time = time.ticks_ms()
                return
                
            time.sleep_ms(10)

        raise RuntimeError(f"CRC check failed. Raw buffer: {list(self._buffer)}")

    def _calculate_temperature(self, temp_data):
        return -45 + 175 * (temp_data / 65535)

    def _calculate_humidity(self, humidity_data):
        return 100 * (humidity_data / 65535)

    def reset(self):
        """Reset the sensor to its default state."""
        self._write_command(_SHTC3_SWRESET)
        time.sleep_ms(1)

    def sleep(self):
        """Put the sensor into a low power sleep mode."""
        self._write_command(_SHTC3_SLEEP)

    def wakeup(self):
        """Wake the sensor from sleep mode."""
        self._write_command(_SHTC3_WAKEUP)
        time.sleep_ms(2)  # MicroPython float sleep can be imprecise; increased to 2ms

    def _write_command(self, command):
        self._cmd_buffer[0] = (command >> 8) & 0xFF
        self._cmd_buffer[1] = command & 0xFF
        self._i2c.writeto(self._address, self._cmd_buffer)

    def _check_crc(self, buffer, start, end):
        # CRC-8 calculation with polynomial 0x31 (x^8 + x^5 + x^4 + 1)
        crc = 0xFF
        for i in range(start, end):
            crc ^= buffer[i]
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc <<= 1
        return crc & 0xFF
