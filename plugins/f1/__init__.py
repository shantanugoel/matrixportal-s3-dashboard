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
        self.display_mode = "idle"

    @property
    def metadata(self):
        return PluginMetadata(
            name="f1",
            version="2.4.0", # Incremented version
            description="Displays F1 race information using the OpenF1 API.",
            refresh_type="pull",
            interval=60,
            default_config={"enabled": False, "show_top": 3}
        )

    def _parse_iso_time(self, iso_str):
        """
        Definitively and safely parse ISO 8601-like time strings.
        Handles YYYY-MM-DDTHH:MM:SS with any trailing characters (Z, timezone, etc.).
        Returns a time.struct_time.
        """
        try:
            if not iso_str or 'T' not in iso_str:
                raise ValueError("Invalid ISO format")

            # The core issue is timezone offsets. We will strip them.
            # Find the 'T' separator. Any '+' or '-' after that is a timezone.
            t_index = iso_str.find('T')
            if '+' in iso_str[t_index:]:
                iso_str = iso_str.split('+')[0]
            
            # A date can have '-', so only check for timezone offset hyphens
            if '-' in iso_str[t_index:]:
                # This is complex, so we simplify: find the last hyphen
                last_hyphen = iso_str.rfind('-')
                if last_hyphen > t_index: # It's in the time part
                    iso_str = iso_str[:last_hyphen]

            # Strip Z for UTC timezone indicator if it exists
            if iso_str.endswith('Z'):
                iso_str = iso_str[:-1]
            
            date_part, time_part = iso_str.split('T')
            
            year, month, day = [int(p) for p in date_part.split('-')]
            
            # Remove microseconds if they exist
            if '.' in time_part:
                time_part = time_part.split('.')[0]
            
            time_components = time_part.split(':')
            hour = int(time_components[0])
            minute = int(time_components[1])
            second = int(time_components[2]) if len(time_components) > 2 else 0
            
            return time.struct_time((year, month, day, hour, minute, second, 0, 0, -1))
        except Exception as e:
            print(f"!!! FAILED TO PARSE TIME STRING: '{iso_str}' due to: {e}")
            # Return a valid CircuitPython time (year 2000) to avoid crashing mktime
            return time.struct_time((2000, 1, 1, 0, 0, 0, 0, 0, -1))

    async def pull(self):
        if not self.network or not self.network.is_connected():
            return None

        try:
            schedule_url = "https://api.openf1.org/v1/sessions?session_type=Race&year=2025"
            schedule_response = await self.network.fetch_json(schedule_url)
            if not schedule_response:
                self.display_mode = "idle"
                return None

            now = time.time()
            live_session, upcoming_session = None, None
            last_session = schedule_response[-1] if schedule_response else None
            
            for session in schedule_response:
                if not session.get('date_start') or not session.get('date_end'):
                    continue

                start_ts = time.mktime(self._parse_iso_time(session['date_start']))
                end_ts = time.mktime(self._parse_iso_time(session['date_end']))

                if start_ts <= now <= end_ts:
                    live_session = session
                    break
                if start_ts > now and upcoming_session is None:
                    upcoming_session = session

            if live_session:
                self.display_mode = "live"
                pos_url = f"https://api.openf1.org/v1/position?session_key={live_session['session_key']}"
                pos_response = await self.network.fetch_json(pos_url)
                drivers = sorted(pos_response, key=lambda x: x['position']) if pos_response else []
                top_drivers = [d['driver_number'] for d in drivers[:self.config.get('show_top', 3)]]
                self.f1_data = {"name": live_session['circuit_short_name'], "drivers": top_drivers}
            elif upcoming_session:
                self.display_mode = "upcoming"
                date_part = upcoming_session['date_start'].split('T')[0].split('-')
                self.f1_data = {"name": upcoming_session['circuit_short_name'], "date": f"{date_part[1]}-{date_part[2]}"}
            elif last_session:
                self.display_mode = "last_result"
                self.f1_data = {"name": f"Last: {last_session['circuit_short_name']}"}
            else:
                self.display_mode = "idle"

            return self.f1_data

        except Exception as e:
            print(f"F1 plugin fetch error: {e}")
            self.display_mode = "idle"
            return None

    def render(self, display_buffer, width, height):
        if self.display_mode == "idle" or not self.f1_data:
            return False

        screen_config = getattr(self, 'screen_config', {})
        region_x, region_y = screen_config.get('x', 0), screen_config.get('y', 0)
        region_width, region_height = screen_config.get('width', width), screen_config.get('height', height)
        
        white, red, yellow = 7, 2, 5
        
        for y in range(region_y, min(region_y + region_height, height)):
            for x in range(region_x, min(region_x + region_width, width)):
                display_buffer[x, y] = 0

        if self.display_mode == "live":
            fit_and_draw_text(display_buffer, f"Live: {self.f1_data['name']}", region_x + 2, region_y + 1, region_width - 4, 7, red, 1)
            drivers_text = " ".join([str(d) for d in self.f1_data.get('drivers', [])])
            fit_and_draw_text(display_buffer, drivers_text, region_x + 2, region_y + 10, region_width - 4, 7, white, 1)
        elif self.display_mode == "upcoming":
            fit_and_draw_text(display_buffer, f"Next: {self.f1_data['name']}", region_x + 2, region_y + 1, region_width - 4, 7, yellow, 1)
            fit_and_draw_text(display_buffer, self.f1_data['date'], region_x + 2, region_y + 10, region_width - 4, 7, white, 1)
        elif self.display_mode == "last_result":
            fit_and_draw_text(display_buffer, self.f1_data['name'], region_x + 2, region_y + 1, region_width - 4, region_height - 2, white, 2)

        return True