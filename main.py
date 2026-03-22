import rlcd
import vector
import sensors
import machine
from machine import Pin, SPI
import time
import uasyncio
import ntptime
import secrets

# --- PINS ---
MOSI_PIN = 12; SCK_PIN = 11; DC_PIN = 5; CS_PIN = 40; RST_PIN = 41

# --- CONFIG ---
TIMEZONE_OFFSET = 0  # Offset in hours from UTC (e.g. -5 for EST, +2 for CEST)

# Raw 8x8 Smiley Data (Small one for Geometry box)
smiley = bytearray([0x3C, 0x42, 0xA5, 0x81, 0xA5, 0x99, 0x42, 0x3C])
# 16x16 WiFi Symbol
wifi_symbol = bytearray([
    0x00, 0x00, 0x1F, 0xF8, 0x70, 0x0E, 0xC0, 0x03,
    0x80, 0x01, 0x07, 0xE0, 0x18, 0x18, 0x60, 0x06,
    0x03, 0xC0, 0x0C, 0x30, 0x00, 0x00, 0x01, 0x80,
    0x01, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
])

async def main():
    print("--- RLCD STARTING ---")

    spi = SPI(2, baudrate=20000000, polarity=0, phase=0, 
              sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN))
    display = rlcd.RLCD(spi, cs=Pin(CS_PIN), dc=Pin(DC_PIN), rst=Pin(RST_PIN))

    display.clear(0) # White Background

    # ================= HEADER =================
    # Black Bar
    display.fill_rect(0, 0, 400, 40, 1) 
    
    # 1. Smiley Logo in Header (Scale 1 = 32x32)
    display.draw_pbm('logo.pbm', 5, 4, scale=1)
    
    # 2. Title: "RLCD"
    # Centered and Clean
    vector.draw(display, "WS RLCD", 50, 10, scale=2, c=0, thickness=2)

    # ================= LEFT SIDE: BITMAPS =================
    # Quadrant 1: Sensors
    display.text_large("1. SENSORS", 10, 50, scale=1)
    display.rect(10, 65, 185, 90, 1)

    # Quadrant 2: Bitmap Text
    display.text_large("2. BITMAP TEXT", 10, 170, scale=1)
    display.rect(10, 185, 185, 105, 1)
    
    display.text("Standard 8x8", 20, 200)
    display.text_large("Scale x2", 20, 220, scale=2)
    
    # "Scale 3" (Fits inside box)
    display.text_large("Scale 3", 20, 250, scale=3)

    # ================= RIGHT SIDE: VECTORS =================
    # Quadrant 3: Geometric Shapes
    display.text_large("3. GEOMETRY", 205, 50, scale=1)
    display.rect(205, 65, 185, 90, 1)
    
    display.fill_rect(220, 80, 30, 30, 1) # Filled Box
    display.rect(260, 80, 30, 30, 1)      # Empty Box
    
    # Cross
    display.line(300, 80, 340, 110, 1)
    display.line(300, 110, 340, 80, 1)
    
    # Raw Bitmap Smiley (Tiny one)
    display.bitmap(360, 90, 8, 8, smiley) 
    
    display.text("Rect/Line/Raw", 220, 130)

    # Quadrant 4: Vector Fonts
    display.text_large("4. VECTOR FONT", 205, 170, scale=1)
    display.rect(205, 185, 185, 105, 1)

    # Compare Thicknesses
    vector.draw(display, "THIN (1)", 215, 200, scale=2, thickness=1)
    vector.draw(display, "BOLD (2)", 215, 230, scale=2, thickness=2)
    vector.draw(display, "HEAVY(3)", 215, 260, scale=2, thickness=3)

    cycle = 0
    cached_wifi = "-"
    cached_ble = "-"

    while True:
        # Update Clock in Header
        display.fill_rect(270, 5, 125, 30, 1) # Clear just the clock area
        current_time = time.time() + int(TIMEZONE_OFFSET * 3600)
        t = time.localtime(current_time)
        clock_str = f"{t[3]:02d}:{t[4]:02d}"
        vector.draw(display, clock_str, 275, 10, scale=2, c=0, thickness=4)

        # Clear the inside of the Sensors box
        display.fill_rect(11, 66, 183, 88, 0)

        # Read sensor values
        temp, hum = sensors.read_temp_humidity()
        volt, perc = sensors.read_battery()
        
        # Format and display the data inside the box
        y_offset = 70
        step = 14
        val_x = 85  # X-coordinate to align all values
        
        display.text("Temp:", 20, y_offset)
        display.text("Hum:", 20, y_offset + step)
        if temp is not None and hum is not None:
            display.text(f"{temp:.1f} C", val_x, y_offset)
            display.text(f"{hum:.1f} %", val_x, y_offset + step)
        else:
            display.text("N/A", val_x, y_offset)
            display.text("N/A", val_x, y_offset + step)
            
        display.text("Batt V:", 20, y_offset + step * 2)
        display.text(f"{volt:.2f}V", val_x, y_offset + step * 2)
        
        display.text("Batt %:", 20, y_offset + step * 3)
        perc_str = f"{perc:.0f}%"
        display.text(perc_str, val_x, y_offset + step * 3)
        
        # Draw Battery Icon
        bx = val_x + len(perc_str) * 8 + 8
        by = y_offset + step * 3 - 2
        display.rect(bx, by, 32, 12, 1)             # Battery body
        display.fill_rect(bx + 32, by + 3, 3, 6, 1) # Battery terminal
        
        num_notches = int(round(perc / 20.0))
        for i in range(num_notches):
            display.fill_rect(bx + 2 + (i * 6), by + 2, 4, 8, 1)
            
        # Draw WiFi info
        display.text("WiFi:", 20, y_offset + step * 4)
        display.text(cached_wifi, val_x, y_offset + step * 4)
        
        wx = val_x + len(cached_wifi) * 8 + 8
        wy = y_offset + step * 4 - 4
        display.bitmap(wx, wy, 16, 16, wifi_symbol)
        
        # Draw BLE info
        display.text("BLE:", 20, y_offset + step * 5)
        display.text(cached_ble, val_x, y_offset + step * 5)
        
        display.show()
        
        # Capture a screenshot for debug or demo purposes
        # display.save_screenshot('output.pbm')

        # Execute background network scans AFTER the screen has been updated
        if cycle == 0 or cycle % 5 == 0:
            print(f"Cycle {cycle}: Performing network scans...")
            sensors.wlan.active(True)
            sensors.ble.active(True)
            
            networks = sensors.scan_wifi()
            cached_wifi = str(len(networks))
            
            if sensors.connect_best_wifi(secrets.WIFI_NETWORKS):
                try:
                    print("Syncing time with NTP...")
                    ntptime.settime()
                    print("Time synced!")
                except Exception as e:
                    print(f"NTP Sync failed: {e}")
            
            devices = await sensors.scan_bluetooth()
            cached_ble = str(len(devices))
            
            # Immediately turn off radios
            sensors.wlan.active(False)
            sensors.ble.active(False)
            
            cycle += 1
            continue # Loop back immediately to redraw with the fresh network data!
            
        print("Idling for 60 seconds...")
        cycle += 1
        await uasyncio.sleep(60)

if __name__ == '__main__':
    uasyncio.run(main())