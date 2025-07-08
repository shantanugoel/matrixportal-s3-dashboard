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
            version="6.1.0", # Correct position logic
            description="Displays the latest F1 race information.",
            refresh_type="pull",
            interval=300,
            default_config={"enabled": False, "show_top": 3, "interval": 300}
        )

    async def pull(self):
        if not self.network or not self.network.is_connected():
            return None

        try:
            latest_session_url = "https://api.openf1.org/v1/sessions?session_key=latest"
            latest_session_resp = await self.network.fetch_json(latest_session_url)
            
            if not latest_session_resp:
                self.f1_data = {"text": "No F1 Data"}
                return self.f1_data

            session = latest_session_resp[0]
            session_key = session['session_key']
            race_name = session.get('circuit_short_name', 'F1 Race')
            
            drivers_url = f"https://api.openf1.org/v1/drivers?session_key={session_key}"
            drivers_resp = await self.network.fetch_json(drivers_url)
            driver_map = {d['driver_number']: d['full_name'] for d in drivers_resp} if drivers_resp else {}

            pos_url = f"https://api.openf1.org/v1/position?session_key={session_key}"
            pos_response = await self.network.fetch_json(pos_url)
            
            if pos_response:
                # Correctly find the latest position for each driver
                latest_positions = {}
                for entry in pos_response:
                    driver_number = entry.get('driver_number')
                    if driver_number:
                        # Since the data is ordered by date, the last entry for a driver is the latest
                        latest_positions[driver_number] = entry
                
                # Convert dict values to a list and sort by position
                final_standings = sorted(latest_positions.values(), key=lambda x: x.get('position', 99))
                
                top_drivers = []
                for p in final_standings[:self.config.get('show_top', 3)]:
                    driver_num = p.get('driver_number')
                    driver_name = driver_map.get(driver_num, f"Driver {driver_num}")
                    last_name = driver_name.split(' ')[-1] if ' ' in driver_name else driver_name
                    top_drivers.append(f"P{p.get('position')} {last_name}")
                
                self.f1_data = {"name": race_name, "results": top_drivers}
            else:
                self.f1_data = {"name": race_name, "results": ["Completed"]}

            return self.f1_data

        except Exception as e:
            print(f"F1 plugin fetch error: {e}")
            self.f1_data = {"text": "F1 API Error"}
            return self.f1_data

    def render(self, display_buffer, width, height):
        if not self.f1_data or not self.f1_data.get('results'):
            return False

        screen_config = getattr(self, 'screen_config', {})
        region_x, region_y = screen_config.get('x', 0), screen_config.get('y', 0)
        region_width, region_height = screen_config.get('width', width), screen_config.get('height', height)
        
        white = 7
        red = 2
        
        for y in range(region_y, min(region_y + region_height, height)):
            for x in range(region_x, min(region_x + region_width, width)):
                display_buffer[x, y] = 0

        fit_and_draw_text(display_buffer, self.f1_data.get('name', 'F1'), 
                         region_x + 2, region_y + 1, 
                         region_width - 4, 7, red, 1)
        
        line_y = region_y + 10
        for driver_text in self.f1_data['results']:
            if line_y >= region_y + region_height:
                break
            fit_and_draw_text(display_buffer, driver_text, 
                             region_x + 2, line_y, 
                             region_width - 4, 7, white, 1)
            line_y += 8

        return True