import time
import adafruit_requests
from core.plugin_interface import PluginInterface, PluginMetadata
try:
    from core.flexible_fonts import fit_and_draw_text
    FLEXIBLE_FONTS = True
except ImportError:
    from core.fonts import draw_text
    FLEXIBLE_FONTS = False
    print("Using fallback fonts for cricket plugin")

def _parse_xml(xml_string, tag):
    """A very simple and non-robust XML parser for RSS feeds."""
    results = []
    start_tag = f"<{tag}>"
    end_tag = f"</{tag}>"
    start_index = 0
    while True:
        start = xml_string.find(start_tag, start_index)
        if start == -1:
            break
        end = xml_string.find(end_tag, start)
        if end == -1:
            break
        results.append(xml_string[start + len(start_tag):end])
        start_index = end + len(end_tag)
    return results

class Plugin(PluginInterface):
    def __init__(self, config):
        super().__init__(config)
        self.network = None
        self.match_data = None
        self.headlines = []
        self.current_headline_index = 0
        self.last_headline_change_time = 0
        self.display_mode = "news" # Default to news

    @property
    def metadata(self):
        return PluginMetadata(
            name="cricket",
            version="5.1.0",
            description="Displays live cricket scores or news from an RSS feed.",
            refresh_type="pull",
            interval=300,
            default_config={
                "enabled": False, 
                "team": "India",
                "rss_url": "https://www.espncricinfo.com/rss/content/story/feeds/6.xml",
                "headline_rotation_minutes": 1,
                "interval": 300
            }
        )

    async def pull(self):
        rss_url = self.config.get("rss_url")
        if not self.network or not self.network.is_connected() or not rss_url:
            return None

        try:
            requests = adafruit_requests.Session(self.network.get_socket_pool(), self.network.get_ssl_context())
            response = requests.get(rss_url, timeout=10)
            
            if response.status_code != 200:
                print(f"Cricket RSS fetch error: Status {response.status_code}")
                self.headlines = ["RSS Fetch Error"]
                response.close()
                return

            xml_text = response.text
            response.close()
            
            # First, get all <item> blocks, then get the <title> from each.
            # This correctly ignores the main <channel> title.
            items = _parse_xml(xml_text, "item")
            titles = []
            for item in items:
                item_titles = _parse_xml(item, "title")
                if item_titles:
                    titles.append(item_titles[0])

            team_name = self.config.get("team", "India").lower()
            
            # Look for a live score in the titles
            for title in titles:
                if " vs " in title.lower() and "/" in title and team_name in title.lower():
                    self.display_mode = "live_score"
                    self.match_data = {"text": self._format_score_title(title)}
                    return self.match_data

            # If no live score, use titles as news headlines
            self.display_mode = "news"
            if titles:
                self.headlines = titles
            else:
                self.headlines = ["No news found"]
            self.current_headline_index = 0
            self.last_headline_change_time = time.monotonic()
            return {"headlines": self.headlines}

        except Exception as e:
            print(f"Cricket plugin RSS fetch error: {e}")
            self.headlines = ["RSS Parse Error"]
            return None

    def _format_score_title(self, title):
        # A simple formatter, might need adjustment based on actual titles
        return title.replace(" - Live Cricket Score", "")

    def render(self, display_buffer, width, height):
        screen_config = getattr(self, 'screen_config', {})
        region_x, region_y = screen_config.get('x', 0), screen_config.get('y', 0)
        region_width, region_height = screen_config.get('width', width), screen_config.get('height', height)
        
        white, green = 1, 3
        
        # Clear the plugin's region before drawing
        for y in range(region_y, min(region_y + region_height, height)):
            for x in range(region_x, min(region_x + region_width, width)):
                display_buffer[x, y] = 0

        text_to_draw = ""
        color = green

        if self.display_mode == "live_score" and self.match_data:
            text_to_draw = self.match_data.get("text", "Score Error")
        elif self.display_mode == "news" and self.headlines:
            rotation_minutes = self.config.get("headline_rotation_minutes", 1)
            if (time.monotonic() - self.last_headline_change_time) > (rotation_minutes * 60):
                self.current_headline_index = (self.current_headline_index + 1) % len(self.headlines)
                self.last_headline_change_time = time.monotonic()
            
            if self.headlines:
                 text_to_draw = self.headlines[self.current_headline_index]
            color = white

        if not text_to_draw:
            return False

        if FLEXIBLE_FONTS:
            word_wrap = self.config.get("word_wrap", True)
            fit_and_draw_text(display_buffer, text_to_draw, 
                             region_x + 1, region_y + 1,
                             region_width - 2, region_height - 2, 
                             color, max_lines=4, word_wrap=word_wrap)
        else:
            draw_text(display_buffer, text_to_draw[:24], region_x + 2, region_y + 2, color)

        return True

