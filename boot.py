"""
Boot configuration for MatrixPortal S3 Dashboard
Initializes PSRAM, sets up safe mode, and handles Wi-Fi initialization
"""
import board
import digitalio
import storage
import supervisor
import microcontroller
import gc

# Enable PSRAM for large frame buffers
try:
    import psram
    psram.enable()
    print("PSRAM enabled")
except ImportError:
    print("PSRAM not available")

# Safe mode check - hold button on boot to enter safe mode
safe_mode_pin = digitalio.DigitalInOut(board.BUTTON)
safe_mode_pin.direction = digitalio.Direction.INPUT
safe_mode_pin.pull = digitalio.Pull.UP

if not safe_mode_pin.value:
    print("Safe mode requested")
    supervisor.set_next_code_file(None)

# Enable external storage if SD card is present
try:
    import sdcardio
    import os
    
    # Try to mount SD card
    spi = board.SPI()
    cs = board.SD_CS
    sdcard = sdcardio.SDCard(spi, cs)
    vfs = storage.VfsFat(sdcard)
    storage.mount(vfs, "/sd")
    print("SD card mounted at /sd")
except Exception as e:
    print(f"SD card not available: {e}")

# Set up USB drive as read-only to prevent corruption during operation
# Comment out for development
# storage.remount("/", readonly=True)

# Garbage collection to free up memory
gc.collect()
print(f"Free memory: {gc.mem_free()}")
