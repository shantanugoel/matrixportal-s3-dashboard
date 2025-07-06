"""
Main entry point for MatrixPortal S3 Dashboard
Handles system initialization and starts the core application
"""
import gc
import time
import supervisor
import microcontroller
import watchdog
import traceback
from core.dashboard import Dashboard

# Global constants
WATCHDOG_TIMEOUT = 15  # seconds
BOOT_DELAY = 2  # seconds

def setup_watchdog():
    """Initialize watchdog timer for system reliability"""
    try:
        wdt = watchdog.WatchDogTimer(timeout=WATCHDOG_TIMEOUT)
        wdt.feed()
        return wdt
    except Exception as e:
        print(f"Watchdog setup failed: {e}")
        return None

def main():
    """Main application loop"""
    print("=== MatrixPortal S3 Dashboard Starting ===")
    print(f"CircuitPython version: {supervisor.runtime.serial_bytes_available}")
    print(f"Board: {microcontroller.cpu.uid}")
    
    # Brief delay to allow serial console to connect
    time.sleep(BOOT_DELAY)
    
    # Initialize watchdog
    wdt = setup_watchdog()
    
    # Initialize dashboard
    dashboard = None
    restart_count = 0
    
    while True:
        try:
            # Feed watchdog
            if wdt:
                wdt.feed()
            
            # Create dashboard instance
            if dashboard is None:
                print("Initializing dashboard...")
                dashboard = Dashboard()
                restart_count = 0
            
            # Run dashboard
            dashboard.run()
            
        except KeyboardInterrupt:
            print("Keyboard interrupt - shutting down")
            break
            
        except Exception as e:
            print(f"Error in main loop: {e}")
            traceback.print_exception(type(e), e, e.__traceback__)
            
            # Increment restart counter
            restart_count += 1
            
            # Clean up
            if dashboard:
                try:
                    dashboard.cleanup()
                except:
                    pass
                dashboard = None
            
            # Force garbage collection
            gc.collect()
            
            # If too many restarts, wait longer
            if restart_count > 5:
                print(f"Multiple restarts ({restart_count}), waiting 30 seconds...")
                time.sleep(30)
            else:
                print(f"Restarting in 5 seconds... (attempt {restart_count})")
                time.sleep(5)
            
            # Reset if too many failures
            if restart_count > 10:
                print("Too many failures, resetting microcontroller...")
                microcontroller.reset()

if __name__ == "__main__":
    main()
