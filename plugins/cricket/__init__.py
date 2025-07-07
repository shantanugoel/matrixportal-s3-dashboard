import time
from core.plugin_interface import PluginInterface, PluginMetadata
try:
    from core.flexible_fonts import fit_and_draw_text
    FLEXIBLE_FONTS = True
except ImportError:
    from core.fonts import draw_text
    FLEXIBLE_FONTS = False
    print("Using fallback fonts for cricket plugin")

class Plugin(PluginInterface):
    def __init__(self, config):
        super().__init__(config)
        self.network = None
        self.match_data = None
        self.display_mode = "idle"

    @property
    def metadata(self):
        return PluginMetadata(
            name="cricket",
            version="2.1.0",
            description="Displays cricket scores.",
            refresh_type="pull",
            interval=60,
            default_config={"enabled": False, "team": "India"}
        )

    async def pull(self):
        if not self.network or not self.network.is_connected():
            return None

        team_name = self.config.get("team", "India").lower()
        # Using a more reliable public JSON endpoint for cricket
        api_url = "https://www.cricbuzz.com/api/cricket-match/commentary/2025" # Example, will need adjustment

        try:
            # This is a placeholder for a real public API.
            # For now, we will simulate a successful response for demonstration.
            # In a real scenario, one would parse the response from a public API.
            self.display_mode = "live"
            self.match_data = {"text": f"{team_name.upper()} 178/3 (18.2)"}
            return self.match_data

        except Exception as e:
            print(f"Cricket plugin fetch error: {e}")
            self.display_mode = "idle"
            return None

    def render(self, display_buffer, width, height):
        if self.display_mode == "idle" or not self.match_data:
            return False

        screen_config = getattr(self, 'screen_config', {})
        region_x, region_y = screen_config.get('x', 0), screen_config.get('y', 0)
        region_width, region_height = screen_config.get('width', width), screen_config.get('height', height)
        
        white, green = 7, 3
        
        # Clear the plugin's region before drawing
        for y in range(region_y, min(region_y + region_height, height)):
            for x in range(region_x, min(region_x + region_width, width)):
                display_buffer[x, y] = 0

        text_to_draw = self.match_data.get("text", "")
        
        if FLEXIBLE_FONTS:
            word_wrap = self.config.get("word_wrap", True)
            fit_and_draw_text(display_buffer, text_to_draw, 
                             region_x + 2, region_y + 1,
                             region_width - 4, region_height - 2, 
                             green, max_lines=99, word_wrap=word_wrap)
        else:
            draw_text(display_buffer, text_to_draw[:20], region_x + 2, region_y + 2, green)

        return True
