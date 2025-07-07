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

    @property
    def metadata(self):
        return PluginMetadata(
            name="f1",
            version="5.0.0", # Final, working version
            description="Displays the latest F1 race information.",
            refresh_type="pull",
            interval=300, # 5 minutes
            default_config={"enabled": False, "show_top": 3}
        )

    async def pull(self):
        """
        Fetches the latest F1 session data (live or most recent).
        This logic is simplified to be robust against simulated future dates.
        """
        if not self.network or not self.network.is_connected():
            return None

        try:
            # This single endpoint always provides the latest session.
            latest_session_url = "https://api.openf1.org/v1/sessions?session_key=latest"
            latest_session_resp = await self.network.fetch_json(latest_session_url)
            
            if not latest_session_resp:
                self.f1_data = {"text": "No F1 Data"}
                return self.f1_data

            session = latest_session_resp[0]
            race_name = session.get('circuit_short_name', 'F1 Race')
            
            # Fetch position data for this session
            pos_url = f"https://api.openf1.org/v1/position?session_key={session['session_key']}"
            pos_response = await self.network.fetch_json(pos_url)
            
            if pos_response:
                # Sort by position and get the top drivers
                drivers = sorted(pos_response, key=lambda x: x.get('position', 99))
                top_drivers = [str(d.get('driver_number', '')) for d in drivers[:self.config.get('show_top', 3)]]
                driver_str = " P".join(top_drivers)
                self.f1_data = {"name": race_name, "results": f"P{driver_str}"}
            else:
                # If no position data, just show the race name
                self.f1_data = {"name": race_name, "results": "Completed"}

            return self.f1_data

        except Exception as e:
            print(f"F1 plugin fetch error: {e}")
            self.f1_data = {"text": "F1 API Error"}
            return self.f1_data

    def render(self, display_buffer, width, height):
        if not self.f1_data:
            return False

        screen_config = getattr(self, 'screen_config', {})
        region_x, region_y = screen_config.get('x', 0), screen_config.get('y', 0)
        region_width, region_height = screen_config.get('width', width), screen_config.get('height', height)
        
        white = 7
        red = 2
        
        # Clear the plugin's region
        for y in range(region_y, min(region_y + region_height, height)):
            for x in range(region_x, min(region_x + region_width, width)):
                display_buffer[x, y] = 0

        # Always display in a two-line format
        # Line 1: Race Name
        fit_and_draw_text(display_buffer, self.f1_data.get('name', 'F1'), 
                         region_x + 2, region_y + 1, 
                         region_width - 4, 7, red, 1)
        
        # Line 2: Results or Status
        fit_and_draw_text(display_buffer, self.f1_data.get('results', ''), 
                         region_x + 2, region_y + 10, 
                         region_width - 4, 7, white, 1)

        return True