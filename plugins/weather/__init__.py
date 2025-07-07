import json
import gc
from core.plugin_interface import PluginInterface, PluginMetadata
try:
    from core.flexible_fonts import fit_and_draw_text
    FLEXIBLE_FONTS = True
except:
    from core.fonts import draw_text
    FLEXIBLE_FONTS = False
    print("Using fallback fonts for weather")

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
        """Render weather information based on configured layout."""
        if not self.weather_data:
            return False
            
        try:
            layout = self.config.get("layout", "single_line") # Default to single_line
            
            if layout == "dual_line":
                return self._render_dual_line(display_buffer, width, height)
            else:
                return self._render_single_line(display_buffer, width, height)
                
        except Exception as e:
            print(f"Weather render error: {e}")
            return False

    def _render_single_line(self, display_buffer, width, height):
        """Render weather in a compact, single-line format."""
        screen_config = getattr(self, 'screen_config', {})
        region_x = screen_config.get('x', 0)
        region_y = screen_config.get('y', 0)
        region_width = screen_config.get('width', width)
        region_height = screen_config.get('height', 12)

        # Colors
        white = 7
        yellow = 5
        blue = 4

        # Clear the region
        for y in range(region_y, min(region_y + region_height, height)):
            for x in range(region_x, min(region_x + region_width, width)):
                display_buffer[x, y] = 0

        # Icon
        icon_x = region_x + 2
        icon_y = region_y + (region_height - 8) // 2 # Center icon vertically
        self._draw_weather_icon(display_buffer, icon_x, icon_y, self.weather_data['condition'], blue)

        # Temperature
        temp_text = f"{self.weather_data['temp']}C"
        temp_x = icon_x + 10
        fit_and_draw_text(display_buffer, temp_text, temp_x, region_y + 2, region_width - temp_x, 7, yellow, 1)

        # Location
        location_text = self.weather_data['location']
        location_x = temp_x + 22 # Position after temp
        fit_and_draw_text(display_buffer, location_text, location_x, region_y + 2, region_width - location_x - 2, 7, white, 1)
        
        return True

    def _render_dual_line(self, display_buffer, width, height):
        """Render weather in a two-line format."""
        screen_config = getattr(self, 'screen_config', {})
        region_x = screen_config.get('x', 0)
        region_y = screen_config.get('y', 0)
        region_width = screen_config.get('width', width)
        region_height = screen_config.get('height', 20)

        # Colors
        white = 7
        yellow = 5
        blue = 4

        # Clear the region
        for y in range(region_y, min(region_y + region_height, height)):
            for x in range(region_x, min(region_x + region_width, width)):
                display_buffer[x, y] = 0

        # Top Line: Icon and Temperature
        icon_x = region_x + 2
        icon_y = region_y + 1
        self._draw_weather_icon(display_buffer, icon_x, icon_y, self.weather_data['condition'], blue)
        
        temp_text = f"{self.weather_data['temp']}C"
        temp_x = icon_x + 12
        fit_and_draw_text(display_buffer, temp_text, temp_x, region_y + 2, region_width - temp_x, 7, yellow, 1)

        # Bottom Line: Location
        location_text = self.weather_data['location']
        fit_and_draw_text(display_buffer, location_text, region_x + 2, region_y + 10, region_width - 4, 7, white, 1)

        return True
    

    
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
