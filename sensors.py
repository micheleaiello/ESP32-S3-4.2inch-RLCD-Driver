from machine import ADC, Pin, I2C, SoftI2C
import shtc3
import time
import network
import bluetooth
import uasyncio

# BATTERY
BATTERY_ADC_PIN = 4
adc = ADC(Pin(BATTERY_ADC_PIN))
adc.atten(ADC.ATTN_11DB)
adc.width(ADC.WIDTH_12BIT)

def read_battery():
    """Reads the battery voltage and returns it along with the percentage."""
    # read_uv() uses the ESP32-S3 factory calibration curve for accurate voltage
    voltage_at_adc_pin = adc.read_uv() / 1000000.0
    
    # Waveshare boards use a 200k/100k voltage divider. 
    # Adjust this slightly (e.g., 2.95 to 3.05) if a physical multimeter reads differently.
    VOLTAGE_MULTIPLIER = 3.0
    actual_battery_voltage = voltage_at_adc_pin * VOLTAGE_MULTIPLIER
    
    # LiPo battery voltage ranges
    BATTERY_MAX_VOLTAGE = 4.2  # Fully charged
    BATTERY_MIN_VOLTAGE = 3.3  # Fully discharged (cut-off voltage)
    
    percentage = 100 * ((actual_battery_voltage - BATTERY_MIN_VOLTAGE) / (BATTERY_MAX_VOLTAGE - BATTERY_MIN_VOLTAGE))
    if percentage > 100:
        percentage = 100
    if percentage < 0:
        percentage = 0
        
    return actual_battery_voltage, percentage

# SHTC3 TEMPERATURE/HUMIDITY
# Using Hardware I2C (id=0) at 400kHz matching the C++ Wire implementation used by VolosR
i2c = I2C(0, scl=Pin(14, pull=Pin.PULL_UP), sda=Pin(13, pull=Pin.PULL_UP), freq=400000)
try:
    sht = shtc3.SHTC3(i2c)
except Exception as e:
    print(f"Failed to initialize SHTC3: {e}")
    sht = None

# ESP32 chips generate heat, causing onboard sensors to read higher than ambient room temperature.
# Check a standalone room thermometer and apply a negative offset here (e.g., -4.0)
TEMP_OFFSET_C = 0.0

def read_temp_humidity():
    """Reads temperature and humidity from the SHTC3 sensor."""
    if sht is None:
        return None, None
    try:
        temperature = sht.temperature + TEMP_OFFSET_C
        humidity = sht.relative_humidity
        return temperature, humidity
    except Exception as e:
        print(f"Error reading from SHTC3: {e}")
        return None, None

# BUTTON
KEY_PIN = 18
key = Pin(KEY_PIN, Pin.IN, Pin.PULL_UP)

def read_button():
    """Reads the state of the KEY button."""
    return "Pressed" if key.value() == 0 else "Not Pressed"

# WIFI
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

def scan_wifi():
    """Scans for available Wi-Fi networks."""
    return wlan.scan()

# BLUETOOTH
ble = bluetooth.BLE()
ble.active(True)

async def scan_bluetooth():
    """Scans for available Bluetooth devices."""
    devices = {}
    def scan_callback(event, data):
        if event == 5:  # _IRQ_SCAN_RESULT
            addr_type, addr, adv_type, rssi, adv_data = data
            devices[bytes(addr)] = rssi

    ble.irq(scan_callback)
    ble.gap_scan(2000, 30000, 30000)
    await uasyncio.sleep_ms(2000)
    ble.gap_scan(None)
    return devices

async def main():
    voltage, percentage = read_battery()
    print(f"Battery Voltage: {voltage:.2f}V")
    print(f"Battery Percentage: {percentage:.0f}%")
    
    temp, hum = read_temp_humidity()
    if temp is not None:
        print(f"Temperature: {temp:.2f}°C")
        print(f"Humidity: {hum:.2f}%")

    button_state = read_button()
    print(f"Button state: {button_state}")

    print("Scanning for Wi-Fi networks...")
    networks = scan_wifi()
    print(f"Found {len(networks)} Wi-Fi networks:")
    for ssid, bssid, channel, rssi, authmode, hidden in networks:
        print(f"  SSID: {ssid.decode('utf-8')}, RSSI: {rssi}")
        
    print("Scanning for Bluetooth devices...")
    devices = await scan_bluetooth()
    print(f"Found {len(devices)} Bluetooth devices:")
    for addr, rssi in devices.items():
        mac_address = addr.hex(':')
        print(f"  Address: {mac_address}, RSSI: {rssi}")

if __name__ == '__main__':
    uasyncio.run(main())
