"""
Digital clock plugin for MatrixPortal S3 Dashboard
Displays current time with readable digits on 64x64 LED matrix
"""
import time
try:
    import adafruit_ntp
    NTP_AVAILABLE = True
except ImportError:
    NTP_AVAILABLE = False
    print("adafruit_ntp not available - clock will use system time")

from core.plugin_interface import PluginInterface, PluginMetadata

class Plugin(PluginInterface):
    def __init__(self, config):
        super().__init__(config)
        
        # NTP configuration
        self.ntp_client = None
        self.ntp_server = config.get('ntp_server', 'pool.ntp.org')
        self.last_ntp_sync = 0
        self.ntp_sync_interval = config.get('ntp_sync_interval', 3600)  # Sync every hour
        self.ntp_enabled = config.get('ntp_enabled', True) and NTP_AVAILABLE
        
        # Configuration
        self.format_24h = config.get('format_24h') if 'format_24h' in config else True
        self.display_seconds = config.get('display_seconds') if 'display_seconds' in config else False
        
        # UTC offset configuration (in hours, can be fractional like 5.5 for IST)
        self.utc_offset_hours = config.get('utc_offset_hours', 5.5)  # Default to IST +5:30
        self.utc_offset = self.utc_offset_hours * 3600  # Convert to seconds
        self.timezone_name = config.get('timezone_name', 'IST')  # Just for display
        
        # Initialize NTP client
        if self.ntp_enabled:
            self._init_ntp()
        
        # Digit patterns for 5x7 font (simplified for LED matrix)
        self.digit_patterns = {
            '0': [
                [1,1,1,1,1],
                [1,0,0,0,1],
                [1,0,0,0,1],
                [1,0,0,0,1],
                [1,0,0,0,1],
                [1,0,0,0,1],
                [1,1,1,1,1]
            ],
            '1': [
                [0,0,1,0,0],
                [0,1,1,0,0],
                [0,0,1,0,0],
                [0,0,1,0,0],
                [0,0,1,0,0],
                [0,0,1,0,0],
                [1,1,1,1,1]
            ],
            '2': [
                [1,1,1,1,1],
                [0,0,0,0,1],
                [0,0,0,0,1],
                [1,1,1,1,1],
                [1,0,0,0,0],
                [1,0,0,0,0],
                [1,1,1,1,1]
            ],
            '3': [
                [1,1,1,1,1],
                [0,0,0,0,1],
                [0,0,0,0,1],
                [1,1,1,1,1],
                [0,0,0,0,1],
                [0,0,0,0,1],
                [1,1,1,1,1]
            ],
            '4': [
                [1,0,0,0,1],
                [1,0,0,0,1],
                [1,0,0,0,1],
                [1,1,1,1,1],
                [0,0,0,0,1],
                [0,0,0,0,1],
                [0,0,0,0,1]
            ],
            '5': [
                [1,1,1,1,1],
                [1,0,0,0,0],
                [1,0,0,0,0],
                [1,1,1,1,1],
                [0,0,0,0,1],
                [0,0,0,0,1],
                [1,1,1,1,1]
            ],
            '6': [
                [1,1,1,1,1],
                [1,0,0,0,0],
                [1,0,0,0,0],
                [1,1,1,1,1],
                [1,0,0,0,1],
                [1,0,0,0,1],
                [1,1,1,1,1]
            ],
            '7': [
                [1,1,1,1,1],
                [0,0,0,0,1],
                [0,0,0,0,1],
                [0,0,0,1,0],
                [0,0,1,0,0],
                [0,1,0,0,0],
                [1,0,0,0,0]
            ],
            '8': [
                [1,1,1,1,1],
                [1,0,0,0,1],
                [1,0,0,0,1],
                [1,1,1,1,1],
                [1,0,0,0,1],
                [1,0,0,0,1],
                [1,1,1,1,1]
            ],
            '9': [
                [1,1,1,1,1],
                [1,0,0,0,1],
                [1,0,0,0,1],
                [1,1,1,1,1],
                [0,0,0,0,1],
                [0,0,0,0,1],
                [1,1,1,1,1]
            ],
            ':': [
                [0,0,0,0,0],
                [0,0,1,0,0],
                [0,0,0,0,0],
                [0,0,0,0,0],
                [0,0,0,0,0],
                [0,0,1,0,0],
                [0,0,0,0,0]
            ]
        }
        
    @property
    def metadata(self):
        return PluginMetadata(
            "clock",
            "1.0.0", 
            "Digital clock display",
            "pull",
            1,  # Update every second
            {
                "enabled": True,
                "format_24h": True,
                "display_seconds": False,
                "utc_offset_hours": 5.5,
                "timezone_name": "IST",
                "ntp_enabled": True,
                "ntp_server": "pool.ntp.org",
                "ntp_sync_interval": 3600
            }
        )
    
    def _init_ntp(self):
        """Initialize NTP client for time synchronization"""
        try:
            if NTP_AVAILABLE:
                # NTP client will be initialized when we need it (lazy loading)
                # because it requires an active network connection
                print(f"NTP client configured for server: {self.ntp_server}")
            else:
                print("NTP not available - using system time")
        except Exception as e:
            print(f"NTP initialization error: {e}")
    
    async def _sync_ntp_time(self):
        """Synchronize time with NTP server"""
        if not self.ntp_enabled or not NTP_AVAILABLE:
            return False
            
        try:
            # Check if we need to sync (don't sync too frequently)
            current_time = time.monotonic()
            if self.last_ntp_sync and current_time - self.last_ntp_sync < self.ntp_sync_interval:
                return True  # Recently synced
            
            # Create NTP client if not exists (requires network)
            if self.ntp_client is None:
                # Import socket pool from network manager if available
                import wifi
                import socketpool
                
                if not wifi.radio.connected:
                    print("No network connection for NTP sync")
                    return False
                
                pool = socketpool.SocketPool(wifi.radio)
                self.ntp_client = adafruit_ntp.NTP(pool, server=self.ntp_server)
            
            # Sync time
            print(f"Syncing time with NTP server: {self.ntp_server}")
            utc_time = self.ntp_client.datetime
            
            # Convert to timestamp and set system time
            # Note: CircuitPython might not allow setting system time
            self.last_ntp_sync = current_time
            print(f"NTP sync successful: {utc_time}")
            return True
            
        except Exception as e:
            print(f"NTP sync failed: {e}")
            return False
    
    async def pull(self):
        """Get current time data"""
        # Try to sync with NTP if enabled and needed
        ntp_synced = await self._sync_ntp_time()
        
        # Get current time and apply timezone offset
        if ntp_synced and self.ntp_client:
            try:
                # Get UTC time from NTP (returns struct_time)
                utc_time_struct = self.ntp_client.datetime
                
                # Calculate timezone offset in hours and minutes
                offset_hours = int(self.utc_offset // 3600)
                offset_minutes = int((self.utc_offset % 3600) // 60)
                
                # Apply offset manually to the time components
                hour = utc_time_struct.tm_hour + offset_hours
                minute = utc_time_struct.tm_min + offset_minutes
                day = utc_time_struct.tm_mday
                
                # Handle minute overflow
                if minute >= 60:
                    minute -= 60
                    hour += 1
                elif minute < 0:
                    minute += 60
                    hour -= 1
                
                # Handle hour overflow
                if hour >= 24:
                    hour -= 24
                    day += 1
                elif hour < 0:
                    hour += 24
                    day -= 1
                
                # Create time struct manually
                current_time = time.struct_time((
                    utc_time_struct.tm_year,
                    utc_time_struct.tm_mon,
                    day,
                    hour,
                    minute,
                    utc_time_struct.tm_sec,
                    0, 0, 0  # weekday, yearday, dst (not used)
                ))
                
            except Exception as e:
                print(f"Error using NTP time: {e}")
                # Fallback to system time with timezone offset
                current_timestamp = time.time()
                local_timestamp = current_timestamp + self.utc_offset
                current_time = time.localtime(local_timestamp)
        else:
            # Use system time with timezone offset
            current_timestamp = time.time()
            local_timestamp = current_timestamp + self.utc_offset
            current_time = time.localtime(local_timestamp)
        
        # Format time string
        if self.format_24h:
            if self.display_seconds:
                time_str = "{:02d}:{:02d}:{:02d}".format(
                    current_time.tm_hour, current_time.tm_min, current_time.tm_sec)
            else:
                time_str = "{:02d}:{:02d}".format(
                    current_time.tm_hour, current_time.tm_min)
        else:
            # 12-hour format
            hour = current_time.tm_hour
            if hour == 0:
                hour = 12
            elif hour > 12:
                hour -= 12
                
            if self.display_seconds:
                time_str = "{:2d}:{:02d}:{:02d}".format(
                    hour, current_time.tm_min, current_time.tm_sec)
            else:
                time_str = "{:2d}:{:02d}".format(hour, current_time.tm_min)
        
        return {
            'time': time_str,
            'hour': current_time.tm_hour,
            'minute': current_time.tm_min,
            'second': current_time.tm_sec,
            'timezone_name': self.timezone_name,
            'utc_offset_hours': self.utc_offset_hours,
            'ntp_enabled': self.ntp_enabled,
            'ntp_synced': ntp_synced,
            'last_ntp_sync': self.last_ntp_sync
        }
    
    def render(self, display_buffer, width, height):
        """Render time digits to LED matrix"""
        try:
            # Get screen configuration for positioning
            screen_config = getattr(self, 'screen_config', {})
            region_x = screen_config.get('x', 0)
            region_y = screen_config.get('y', 16) 
            region_width = screen_config.get('width', width)
            region_height = screen_config.get('height', 32)
            
            # Clear only the clock region
            for y in range(region_y, min(region_y + region_height, height)):
                for x in range(region_x, min(region_x + region_width, width)):
                    display_buffer[x, y] = 0
            
            # Get time string
            time_str = self.data.get('time', '--:--')
            
            # Calculate starting position to center the time horizontally
            char_width = 5
            char_spacing = 1
            total_width = len(time_str) * (char_width + char_spacing) - char_spacing
            start_x = region_x + (region_width - total_width) // 2
            # Use the exact y from the config, no vertical centering
            start_y = region_y
            
            # Draw each character
            x_pos = start_x
            for char in time_str:
                if char in self.digit_patterns:
                    self._draw_digit(display_buffer, char, x_pos, start_y, width, height)
                x_pos += char_width + char_spacing
            
            return True
            
        except Exception as e:
            print("Clock render error:", e)
            return False
    
    def _draw_digit(self, buffer, digit, x, y, width, height):
        """Draw a single digit or colon on the display"""
        pattern = self.digit_patterns.get(digit, [])
        
        for row_idx, row in enumerate(pattern):
            for col_idx, pixel in enumerate(row):
                pixel_x = x + col_idx
                pixel_y = y + row_idx
                
                # Check bounds
                if 0 <= pixel_x < width and 0 <= pixel_y < height:
                    if pixel:
                        # Use different colors for different elements
                        if digit == ':':
                            buffer[pixel_x, pixel_y] = 2  # Different color for colon
                        else:
                            buffer[pixel_x, pixel_y] = 1  # Main digit color
