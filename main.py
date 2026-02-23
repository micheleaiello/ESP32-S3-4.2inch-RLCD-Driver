import rlcd
import vector
from machine import Pin, SPI
import time

# --- PINS ---
MOSI_PIN = 12; SCK_PIN = 11; DC_PIN = 5; CS_PIN = 40; RST_PIN = 41

# Raw 8x8 Smiley Data (Small one for Geometry box)
smiley = bytearray([0x3C, 0x42, 0xA5, 0x81, 0xA5, 0x99, 0x42, 0x3C])

def main():
    print("--- RLCD SMILEY DEMO ---")
    spi = SPI(2, baudrate=20000000, polarity=0, phase=0, 
              sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN))
    display = rlcd.RLCD(spi, cs=Pin(CS_PIN), dc=Pin(DC_PIN), rst=Pin(RST_PIN))

    display.clear(0) # White Background

    # ================= HEADER =================
    # Black Bar
    display.fill_rect(0, 0, 400, 40, 1) 
    
    # 1. Smiley Logo in Header (Scale 1 = 32x32)
    display.draw_pbm('logo.pbm', 5, 4, scale=1)
    
    # 2. Title: "RLCD STUDIO"
    # Centered and Clean
    vector.draw(display, "RLCD STUDIO", 70, 10, scale=2, c=0, thickness=2)

    # ================= LEFT SIDE: BITMAPS =================
    # Quadrant 1: PBM Images
    display.text_large("1. IMAGES (PBM)", 10, 50, scale=1)
    display.rect(10, 65, 185, 90, 1)
    
    # Smiley Scale x1
    display.draw_pbm('logo.pbm', 30, 80, scale=1)
    display.text("x1", 35, 120)
    
    # Smiley Scale x2
    display.draw_pbm('logo.pbm', 90, 75, scale=2)
    display.text("x2", 110, 140)

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

    print("Updating Screen...")
    display.show()
    display.save_screenshot('output.pbm')
    print("Keep Smiling!")

if __name__ == '__main__':
    main()