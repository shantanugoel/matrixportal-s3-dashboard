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
            version="3.0.0",
            description="Displays cricket scores using Sportmonks API.",
            refresh_type="pull",
            interval=60,
            default_config={
                "enabled": False, 
                "team": "India",
                "sportmonks_api_key": ""
            }
        )

    async def pull(self):
        if not self.network or not self.network.is_connected():
            self.display_mode = "idle"
            return None

        api_key = self.config.get("sportmonks_api_key")
        if not api_key or api_key == "${SPORTMONKS_API_KEY}":
            print("Sportmonks API key not configured in config.json")
            self.display_mode = "idle"
            self.match_data = {"text": "No API Key"}
            return self.match_data

        team_name = self.config.get("team", "India").lower()
        api_url = f"https://cricket.sportmonks.com/api/v2.0/livescores?api_token={api_key}&include=localteam,visitorteam"

        try:
            json_data = await self.network.fetch_json(api_url)
            
            if not json_data or 'data' not in json_data:
                print("Cricket plugin: Invalid or empty response from API")
                self.display_mode = "live" # Set to live to display the error
                self.match_data = {"text": "API Error"}
                return self.match_data

            live_matches = json_data.get('data', [])
            if not live_matches:
                self.display_mode = "live" # Set to live to display the message
                self.match_data = {"text": "No Live Matches"}
                return self.match_data

            for match in live_matches:
                local_team = match.get('localteam', {}).get('name', '').lower()
                visitor_team = match.get('visitorteam', {}).get('name', '').lower()

                if team_name in local_team or team_name in visitor_team:
                    self.display_mode = "live"
                    score_summary = self._format_score(match)
                    self.match_data = {"text": score_summary}
                    return self.match_data

            self.display_mode = "idle"
            self.match_data = {"text": f"No match for {team_name.upper()}"}
            return self.match_data

        except Exception as e:
            print(f"Cricket plugin fetch error: {e}")
            self.display_mode = "idle"
            self.match_data = {"text": "Fetch Error"}
            return None

    def _format_score(self, match):
        local_team = match.get('localteam', {}).get('code', 'T1')
        visitor_team = match.get('visitorteam', {}).get('code', 'T2')
        
        live_score = ""
        for run in match.get('runs', []):
            if run.get('live', False):
                live_score = f"{run.get('score', 0)}/{run.get('wickets', 0)} ({run.get('overs', 0)})"
                break
        
        return f"{local_team.upper()} vs {visitor_team.upper()}\n{live_score}"

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
                             region_x + 1, region_y + 1,
                             region_width - 2, region_height - 2, 
                             green, max_lines=3, word_wrap=word_wrap)
        else:
            # Fallback for older font system
            lines = text_to_draw.split('\n')
            draw_text(display_buffer, lines[0][:12], region_x + 2, region_y + 2, green)
            if len(lines) > 1:
                draw_text(display_buffer, lines[1][:12], region_x + 2, region_y + 10, green)

        return True
