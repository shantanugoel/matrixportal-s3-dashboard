import json
import gc
import time
from core.plugin_interface import PluginInterface, PluginMetadata
try:
    from core.flexible_fonts import fit_and_draw_text
    FLEXIBLE_FONTS = True
except:
    from core.fonts import draw_text
    FLEXIBLE_FONTS = False
    print("Using fallback fonts for news plugin")

class Plugin(PluginInterface):
    def __init__(self, config):
        super().__init__(config)
        self.network = None  # Will be set by plugin manager
        self.articles = []
        self.current_article = None
        self.last_article_change = 0
        self.last_fetch = 0
        
    @property
    def metadata(self):
        return PluginMetadata(
            name="news",
            version="1.0.0",
            description="Displays news headlines from a configurable RSS feed.",
            refresh_type="pull",
            interval=3600,  # 1 hour to fetch new articles
            default_config={
                "enabled": False,
                "rss_url": "http://feeds.bbci.co.uk/news/rss.xml",
                "article_rotation_minutes": 5,
                "max_articles": 25
            }
        )
    
    async def pull(self):
        """Fetch articles from an RSS feed via rss2json."""
        if not self.network or not self.network.is_connected():
            return None
            
        rss_url = self.config.get("rss_url")
        if not rss_url:
            print("News plugin: rss_url not configured.")
            return None

        api_url = f"https://api.rss2json.com/v1/api.json?rss_url={rss_url}"
            
        try:
            response = await self.network.fetch_json(api_url)
            
            if not response or response.get('status') != 'ok' or not response.get('items'):
                print(f"News plugin: Failed to fetch or parse RSS feed. Status: {response.get('status')}")
                return None
            
            max_articles = self.config.get("max_articles", 25)
            
            # Extract titles from the articles
            self.articles = [
                {"title": item.get("title", "No Title")}
                for item in response['items'][:max_articles] if item.get("title")
            ]
            
            if self.articles:
                self.last_fetch = time.monotonic()
                # Set initial article if none selected
                if not self.current_article:
                    self._select_random_article()
                return {"articles_count": len(self.articles)}
                
        except Exception as e:
            print(f"News plugin fetch error: {e}")
            
        return None
    
    def _select_random_article(self):
        """Select a random article from the fetched articles."""
        if not self.articles:
            return
            
        current_time = time.monotonic()
        index = int(current_time) % len(self.articles)
        self.current_article = self.articles[index]
        self.last_article_change = current_time
    
    def _should_change_article(self):
        """Check if it's time to change the current article."""
        if not self.current_article or not self.articles:
            return True
            
        rotation_minutes = self.config.get("article_rotation_minutes", 5)
        rotation_seconds = rotation_minutes * 60
        
        return (time.monotonic() - self.last_article_change) >= rotation_seconds
    
    def render(self, display_buffer, width, height):
        """Render the current news headline."""
        if not self.articles:
            return False
            
        if self._should_change_article():
            self._select_random_article()
            
        if not self.current_article:
            return False
            
        try:
            screen_config = getattr(self, 'screen_config', {})
            region_x = screen_config.get('x', 0)
            region_y = screen_config.get('y', 48)
            region_width = screen_config.get('width', width)
            region_height = screen_config.get('height', 16)
            
            # Colors
            white = 7
            blue = 4
            
            # Clear the news area
            for y in range(region_y, min(region_y + region_height, height)):
                for x in range(region_x, min(region_x + region_width, width)):
                    display_buffer[x, y] = 0
            
            title = self.current_article["title"]
            
            title_area_width = region_width - 4
            title_area_height = region_height - 2
            
            if FLEXIBLE_FONTS:
                # Use all available space, with no line limit
                fit_and_draw_text(display_buffer, title, 
                                 region_x + 2, region_y + 1,
                                 title_area_width, title_area_height, white, max_lines=99) # Use a large number for max_lines
            else:
                # Fallback to simple font
                title_short = title[:12] + "..." if len(title) > 12 else title
                draw_text(display_buffer, title_short, region_x + 2, region_y + 2, white)
            
            return True
            
        except Exception as e:
            print(f"News render error: {e}")
            return False
