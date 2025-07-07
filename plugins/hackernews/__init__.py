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
    print("Using fallback fonts for hackernews")

class Plugin(PluginInterface):
    def __init__(self, config):
        super().__init__(config)
        self.network = None  # Will be set by plugin manager
        self.stories = []
        self.current_story = None
        self.last_story_change = 0
        self.last_fetch = 0
        
    @property
    def metadata(self):
        return PluginMetadata(
            name="hackernews",
            version="1.0.0",
            description="Hacker News headlines from top 50 stories",
            refresh_type="pull",
            interval=1800,  # 30 minutes to fetch new stories
            default_config={
                "enabled": True,
                "position": "bottom",
                "height": 16,  # pixels from bottom
                "story_rotation_minutes": 5,  # Change story every 5 minutes
                "max_stories": 50,
                "max_title_length": 60
            }
        )
    
    async def pull(self):
        """Fetch top stories from Hacker News API"""
        if not self.network or not self.network.is_connected():
            return None
            
        try:
            # Fetch top story IDs
            top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            story_ids = await self.network.fetch_json(top_stories_url)
            
            if not story_ids:
                return None
            
            # Get the first N stories (default 50)
            max_stories = self.config.get("max_stories", 50)
            selected_ids = story_ids[:max_stories]
            
            # Fetch story details for each ID
            stories = []
            for story_id in selected_ids[:10]:  # Limit to first 10 for memory
                try:
                    story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                    story_data = await self.network.fetch_json(story_url)
                    
                    if story_data and story_data.get("title"):
                        stories.append({
                            "id": story_id,
                            "title": story_data["title"],
                            "url": story_data.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                            "score": story_data.get("score", 0),
                            "by": story_data.get("by", "unknown")
                        })
                        
                    # Yield control occasionally to prevent blocking
                    if len(stories) % 3 == 0:
                        gc.collect()
                        
                except Exception as e:
                    print(f"Error fetching story {story_id}: {e}")
                    continue
            
            if stories:
                self.stories = stories
                self.last_fetch = time.monotonic()
                # Set initial story if none selected
                if not self.current_story:
                    self._select_random_story()
                return {"stories_count": len(stories)}
                
        except Exception as e:
            print(f"HackerNews fetch error: {e}")
            
        return None
    
    def _select_random_story(self):
        """Select a random story from the fetched stories"""
        if not self.stories:
            return
            
        # Simple pseudo-random selection using current time
        current_time = time.monotonic()
        index = int(current_time) % len(self.stories)
        self.current_story = self.stories[index]
        self.last_story_change = current_time
    
    def _should_change_story(self):
        """Check if it's time to change the current story"""
        if not self.current_story or not self.stories:
            return True
            
        rotation_minutes = self.config.get("story_rotation_minutes", 5)
        rotation_seconds = rotation_minutes * 60
        
        return (time.monotonic() - self.last_story_change) >= rotation_seconds
    
    def render(self, display_buffer, width, height):
        """Render current Hacker News headline at the bottom"""
        if not self.stories:
            return False
            
        # Check if we should change the story
        if self._should_change_story():
            self._select_random_story()
            
        if not self.current_story:
            return False
            
        try:
            # Get screen configuration for positioning
            screen_config = getattr(self, 'screen_config', {})
            region_x = screen_config.get('x', 0)
            region_y = screen_config.get('y', 48)
            region_width = screen_config.get('width', width)
            region_height = screen_config.get('height', 16)
            max_title_length = self.config.get("max_title_length", 60)
            
            # Colors
            white = 7
            orange = 5  # HN orange theme
            gray = 3
            
            # Clear the HN area
            for y in range(region_y, min(region_y + region_height, height)):
                for x in range(region_x, min(region_x + region_width, width)):
                    display_buffer[x, y] = 0
            
            # Prepare title text
            title = self.current_story["title"]
            
            # Use most of the region for the title (3 lines max)
            title_area_width = region_width - 4  # Small margin
            title_area_height = region_height - 2  # Small margin
            
            if FLEXIBLE_FONTS:
                # Render title, using configurable word wrap
                word_wrap = self.config.get("word_wrap", True)
                fit_and_draw_text(display_buffer, title, 
                                 region_x + 2, region_y + 1,
                                 title_area_width, title_area_height, white, 3, word_wrap=word_wrap)
            else:
                # Fallback to simple font
                # Truncate title for fallback
                title_short = title[:12] + "..." if len(title) > 12 else title
                draw_text(display_buffer, title_short, region_x + 2, region_y + 2, white)
            
            return True
            
        except Exception as e:
            print(f"HackerNews render error: {e}")
            return False
    

