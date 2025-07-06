import json
import gc
from core.plugin_interface import PluginInterface, PluginMetadata
from core.fonts import draw_text, draw_char

class Plugin(PluginInterface):
    def __init__(self, config):
        super().__init__(config)
        self.network = None  # Will be set by plugin manager
        self.weather_data = None
        self.last_update = 0
        
    @property
    def metadata(self):
        return PluginMetadata(
            name="weather",
            version="1.0.0",
            description="Weather display using wttr.in API",
            refresh_type="pull",
            interval=600,  # 10 minutes
            default_config={
                "enabled": True,
                "location": "auto",  # auto-detect or specify city name
                "position": "top",
                "height": 16,  # pixels from top
                "units": "metric"
            }
        )
    
    async def pull(self):
        """Fetch weather data from wttr.in"""
        if not self.network or not self.network.is_connected():
            return None
            
        try:
            location = self.config.get("location", "auto")
            if location == "auto":
                location = ""  # wttr.in auto-detects based on IP
            
            url = f"https://wttr.in/{location}?format=j1"
            response = await self.network.fetch_json(url)
            
            if response and "current_condition" in response:
                current = response["current_condition"][0]
                self.weather_data = {
                    "temp": current.get("temp_C", "?"),
                    "condition": current.get("weatherDesc", [{}])[0].get("value", "Unknown"),
                    "humidity": current.get("humidity", "?"),
                    "wind": current.get("windspeedKmph", "?"),
                    "location": response.get("nearest_area", [{}])[0].get("areaName", [{}])[0].get("value", "Unknown")
                }
                gc.collect()
                return self.weather_data
                
        except Exception as e:
            print(f"Weather fetch error: {e}")
            
        return None
    
    def render(self, display_buffer, width, height):
        """Render weather information at the top"""
        if not self.weather_data:
            return False
            
        try:
            # Get screen configuration for positioning
            screen_config = getattr(self, 'screen_config', {})
            region_x = screen_config.get('x', 0)
            region_y = screen_config.get('y', 0)
            region_width = screen_config.get('width', width)
            region_height = screen_config.get('height', 16)
            
            # Colors (using basic color indices for CircuitPython)
            white = 7
            blue = 1
            yellow = 6
            
            # Clear the weather area
            for y in range(region_y, min(region_y + region_height, height)):
                for x in range(region_x, min(region_x + region_width, width)):
                    display_buffer[x, y] = 0
            
            # Simple text rendering (placeholder - in real implementation would use bitmap fonts)
            temp_text = f"{self.weather_data['temp']}C"
            condition_text = self.weather_data['condition'][:12]  # Truncate
            
            # Render temperature in region
            draw_text(display_buffer, temp_text, region_x + 2, region_y + 2, yellow, region_width - 16)
            
            # Render condition below temperature  
            draw_text(display_buffer, condition_text, region_x + 2, region_y + 10, white, region_width - 4)
            
            # Simple weather icon placeholder (a few pixels representing weather)
            icon_x = region_x + region_width - 10
            self._draw_weather_icon(display_buffer, icon_x, region_y + 2, self.weather_data['condition'], blue)
            
            return True
            
        except Exception as e:
            print(f"Weather render error: {e}")
            return False
    

    
    def _draw_weather_icon(self, buffer, x, y, condition, color):
        """Draw a simple weather icon"""
        condition_lower = condition.lower()
        
        # Simple 8x8 weather icons using pixels
        if "sun" in condition_lower or "clear" in condition_lower:
            # Sun icon - circle with rays
            for i in range(3, 6):
                for j in range(3, 6):
                    buffer[x + i, y + j] = color
        elif "rain" in condition_lower:
            # Rain icon - vertical lines
            for i in range(2, 7, 2):
                for j in range(8):
                    buffer[x + i, y + j] = color
        elif "cloud" in condition_lower:
            # Cloud icon - lumpy shape
            for i in range(1, 7):
                for j in range(2, 6):
                    if (i + j) % 3 != 0:
                        buffer[x + i, y + j] = color
        else:
            # Default icon - question mark
            pattern = [
                [0,1,1,0],
                [1,0,0,1],
                [0,0,1,0],
                [0,1,0,0],
                [0,0,0,0],
                [0,1,0,0]
            ]
            for py, row in enumerate(pattern):
                for px, pixel in enumerate(row):
                    if pixel and y + py < 64 and x + px < 64:
                        buffer[x + px, y + py] = color
