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
                "sportmonks_api_key": "",
                "interval": 60
            }
        )

    async def pull(self):
        if not self.network or not self.network.is_connected():
            self.display_mode = "idle"
            return None

        api_key = self.config.get("sportmonks_api_key")
        if not api_key or api_key == "${SPORTMONKS_API_KEY}":
            print("Sportmonks API key not configured in config.json")
            self.display_mode = "live"
            self.match_data = {"text": "No API Key"}
            return self.match_data

        team_name = self.config.get("team", "India")
        
        # First, check for live matches
        live_api_url = f"https://cricket.sportmonks.com/api/v2.0/livescores?api_token={api_key}&include=localteam,visitorteam"
        json_data = await self.network.fetch_json(live_api_url)

        if json_data and json_data.get('data'):
            for match in json_data['data']:
                local_team_name = match.get('localteam', {}).get('name', '').lower()
                visitor_team_name = match.get('visitorteam', {}).get('name', '').lower()
                if team_name.lower() in local_team_name or team_name.lower() in visitor_team_name:
                    self.display_mode = "live"
                    self.match_data = {"text": self._format_score(match)}
                    return self.match_data

        # If no live match, find the next fixture
        try:
            # Get team ID
            teams_url = f"https://cricket.sportmonks.com/api/v2.0/teams?api_token={api_key}&filter[name]={team_name}"
            teams_data = await self.network.fetch_json(teams_url)
            if not teams_data or not teams_data.get('data'):
                self.display_mode = "live"
                self.match_data = {"text": f"Team {team_name} not found"}
                return self.match_data
            
            team_id = teams_data['data'][0]['id']

            # Get all upcoming fixtures sorted by date
            fixtures_url = f"https://cricket.sportmonks.com/api/v2.0/fixtures?api_token={api_key}&filter[status]=NS&sort=starting_at&include=localteam,visitorteam"
            fixtures_data = await self.network.fetch_json(fixtures_url)

            if not fixtures_data or not fixtures_data.get('data'):
                self.display_mode = "live"
                self.match_data = {"text": f"No upcoming matches found"}
                return self.match_data

            # Find the first match for the configured team
            for match in fixtures_data['data']:
                local_team_id = match.get('localteam', {}).get('id')
                visitor_team_id = match.get('visitorteam', {}).get('id')
                if team_id == local_team_id or team_id == visitor_team_id:
                    self.display_mode = "live"
                    self.match_data = {"text": self._format_fixture(match)}
                    return self.match_data

            # If no match was found in the upcoming list
            self.display_mode = "live"
            self.match_data = {"text": f"No upcoming match for {team_name}"}
            return self.match_data

        except Exception as e:
            print(f"Cricket plugin fixture fetch error: {e}")
            self.display_mode = "live"
            self.match_data = {"text": "Fixture Error"}
            return None

    def _format_fixture(self, match):
        local_team = match.get('localteam', {}).get('code', 'T1')
        visitor_team = match.get('visitorteam', {}).get('code', 'T2')
        date_str = match.get('starting_at', '').split('T')[0]
        return f"{local_team} vs {visitor_team}\non {date_str}"

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
