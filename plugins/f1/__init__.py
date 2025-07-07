import time
from core.plugin_interface import PluginInterface, PluginMetadata
try:
    from core.flexible_fonts import fit_and_draw_text
    FLEXIBLE_FONTS = True
except ImportError:
    from core.fonts import draw_text
    FLEXIBLE_FONTS = False
    print("Using fallback fonts for f1 plugin")

class Plugin(PluginInterface):
    def __init__(self, config):
        super().__init__(config)
        self.network = None
        self.f1_data = None
        self.display_mode = "idle" # Modes: idle, live, upcoming, last_result

    @property
    def metadata(self):
        return PluginMetadata(
            name="f1",
            version="1.0.0",
            description="Displays F1 race information.",
            refresh_type="pull",
            interval=300,  # 5 minutes
            default_config={
                "enabled": False,
                "show_top": 3
            }
        )

    async def pull(self):
        """Fetch and process F1 race data from Ergast API."""
        if not self.network or not self.network.is_connected():
            return None

        api_url = "http://ergast.com/api/f1/current.json"

        try:
            response = await self.network.fetch_json(api_url)
            if not response or not response.get('MRData', {}).get('RaceTable', {}).get('Races'):
                self.display_mode = "idle"
                return None

            races = response['MRData']['RaceTable']['Races']
            now = time.time()
            
            live_race = None
            upcoming_race = None
            last_race = races[-1] if races else None

            for race in races:
                race_time_str = f"{race['date']}T{race['time']}"
                # Ergast uses 'Z' for UTC, which we handle by replacing it
                race_timestamp = time.mktime(time.strptime(race_time_str.replace('Z', ''), "%Y-%m-%dT%H:%M:%S"))
                
                # Check for a live race (assuming a race is "live" for 3 hours)
                if now >= race_timestamp and now < race_timestamp + (3 * 3600):
                    live_race = race
                    break
                
                if race_timestamp > now:
                    if not upcoming_race:
                        upcoming_race = race
            
            if live_race:
                self.display_mode = "live"
                # For live, we'd ideally fetch live standings. For now, we show the race name.
                # A real implementation would call another API endpoint for live data.
                self.f1_data = {"text": f"{live_race['raceName']}"}
            elif upcoming_race:
                self.display_mode = "upcoming"
                self.f1_data = {"text": f"{upcoming_race['raceName']} {upcoming_race['date']}"}
            elif last_race:
                self.display_mode = "last_result"
                # Fetch last race results
                last_race_url = "http://ergast.com/api/f1/current/last/results.json"
                last_race_response = await self.network.fetch_json(last_race_url)
                if last_race_response and last_race_response.get('MRData', {}).get('RaceTable', {}).get('Races'):
                    results = last_race_response['MRData']['RaceTable']['Races'][0]['Results']
                    winner = results[0]['Driver']['code']
                    self.f1_data = {"text": f"{last_race['raceName']}: {winner} won"}
                else:
                    self.f1_data = {"text": f"Results for {last_race['raceName']}"}
            else:
                self.display_mode = "idle"
                self.f1_data = {"text": "No F1 data"}

            return self.f1_data

        except Exception as e:
            print(f"F1 plugin fetch error: {e}")
            self.display_mode = "idle"
            return None

    def render(self, display_buffer, width, height):
        """Render the F1 information."""
        if self.display_mode == "idle" or not self.f1_data:
            return False

        try:
            screen_config = getattr(self, 'screen_config', {})
            region_x = screen_config.get('x', 0)
            region_y = screen_config.get('y', 0)
            region_width = screen_config.get('width', width)
            region_height = screen_config.get('height', height)
            
            white = 7
            red = 2
            yellow = 5

            # Clear the region
            for y in range(region_y, min(region_y + region_height, height)):
                for x in range(region_x, min(region_x + region_width, width)):
                    display_buffer[x, y] = 0

            prefix = ""
            color = white
            if self.display_mode == "live":
                prefix = "Live: "
                color = red
            elif self.display_mode == "upcoming":
                prefix = "Next: "
                color = yellow
            elif self.display_mode == "last_result":
                prefix = "Last: "
                color = white

            text_to_draw = prefix + self.f1_data.get("text", "")

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
            print(f"F1 render error: {e}")
            return False
