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
        self.display_mode = "idle" # Modes: idle, live, upcoming, last_result

    @property
    def metadata(self):
        return PluginMetadata(
            name="cricket",
            version="1.0.0",
            description="Displays cricket scores for a specific team.",
            refresh_type="pull",
            interval=300,  # 5 minutes
            default_config={
                "enabled": False,
                "team": "IND", # Team code (e.g., IND, AUS, ENG)
                "rss_url": "https://www.espncricinfo.com/rss/livescores.xml"
            }
        )

    async def pull(self):
        """Fetch and process cricket match data from a reliable RSS feed."""
        if not self.network or not self.network.is_connected():
            return None

        team_code = self.config.get("team", "").upper()
        # Using a general cricket RSS feed
        rss_url = "https://www.espncricinfo.com/rss/content/story/feeds/0.xml"
        api_url = f"https://api.rss2json.com/v1/api.json?rss_url={rss_url}"

        try:
            response = await self.network.fetch_json(api_url)
            if not response or response.get('status') != 'ok' or not response.get('items'):
                self.display_mode = "idle"
                return None

            items = response.get('items', [])
            
            relevant_match = None
            for item in items:
                title = item.get('title', '')
                if team_code in title.upper():
                    relevant_match = item
                    break 
            
            if relevant_match:
                # Simplified logic: show the latest news/score for the team
                self.display_mode = "live" # Use 'live' to show with a green prefix
                self.match_data = self._parse_title(relevant_match['title'])
            else:
                self.display_mode = "idle"
                self.match_data = {"text": f"No {team_code} match found"}

            return self.match_data

        except Exception as e:
            print(f"Cricket plugin fetch error: {e}")
            self.display_mode = "idle"
            return None

    def _parse_title(self, title):
        # This is a simplification; real parsing would be more complex
        # For now, we just clean up the title a bit
        return {"text": title.replace('&amp;', '&')}

    def render(self, display_buffer, width, height):
        """Render the cricket information."""
        if self.display_mode == "idle" or not self.match_data:
            return False

        try:
            screen_config = getattr(self, 'screen_config', {})
            region_x = screen_config.get('x', 0)
            region_y = screen_config.get('y', 0)
            region_width = screen_config.get('width', width)
            region_height = screen_config.get('height', height)
            
            white = 7
            green = 3
            yellow = 5

            # Clear the region
            for y in range(region_y, min(region_y + region_height, height)):
                for x in range(region_x, min(region_x + region_width, width)):
                    display_buffer[x, y] = 0

            prefix = ""
            color = white
            if self.display_mode == "live":
                prefix = "Live: "
                color = green
            elif self.display_mode == "upcoming":
                prefix = "Next: "
                color = yellow
            elif self.display_mode == "last_result":
                prefix = "Last: "
                color = white

            text_to_draw = prefix + self.match_data.get("text", "")

            if FLEXIBLE_FONTS:
                word_wrap = self.config.get("word_wrap", True)
                fit_and_draw_text(display_buffer, text_to_draw, 
                                 region_x + 2, region_y + 1,
                                 region_width - 4, region_height - 2, 
                                 color, max_lines=99, word_wrap=word_wrap)
            else:
                draw_text(display_buffer, text_to_draw[:20], region_x + 2, region_y + 2, color)

            return True

        except Exception as e:
            print(f"Cricket render error: {e}")
            return False
