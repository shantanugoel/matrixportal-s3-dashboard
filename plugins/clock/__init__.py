"""
Digital clock plugin for MatrixPortal S3 Dashboard
Displays current time with readable digits on 64x64 LED matrix
"""
import time
from core.plugin_interface import PluginInterface, PluginMetadata

class Plugin(PluginInterface):
    def __init__(self, config):
        super().__init__(config)
        
        # Configuration
        self.format_24h = config.get('format_24h') if 'format_24h' in config else True
        self.display_seconds = config.get('display_seconds') if 'display_seconds' in config else False
        
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
                "display_seconds": False
            }
        )
    
    async def pull(self):
        """Get current time data"""
        current_time = time.localtime()
        
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
            'second': current_time.tm_sec
        }
    
    def render(self, display_buffer, width, height):
        """Render time digits to LED matrix"""
        try:
            # Clear the display
            for y in range(height):
                for x in range(width):
                    display_buffer[x, y] = 0
            
            # Get time string
            time_str = self.data.get('time', '--:--')
            
            # Calculate starting position to center the time
            char_width = 5
            char_spacing = 1
            total_width = len(time_str) * (char_width + char_spacing) - char_spacing
            start_x = (width - total_width) // 2
            start_y = (height - 7) // 2  # 7 is digit height
            
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
