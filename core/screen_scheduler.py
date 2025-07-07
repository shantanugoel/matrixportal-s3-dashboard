"""
Screen-based scheduler for MatrixPortal S3 Dashboard
Manages screen rotation and plugin data updates within screens
"""
import asyncio
import time
import gc
from .screen_manager import ScreenManager
import sys

class ScreenScheduler:
    """Manages screen rotation and plugin data pulling for all screens"""
    
    def __init__(self, display_engine, screen_manager):
        self.display_engine = display_engine
        self.screen_manager = screen_manager
        self.running = False
        
        # Task management
        self.tasks = set()
        self.display_task = None
        self.pull_tasks = {}  # screen_name -> task
        
        # Timing
        self.render_fps = 10  # Target FPS for display updates
        self.pull_interval = 1  # Check for pull updates every second
        
    async def start(self):
        """Start the screen scheduler"""
        if self.running:
            return
            
        self.running = True
        print("Starting screen scheduler...")
        
        # Start main display loop
        self.display_task = asyncio.create_task(self._display_loop())
        
        # Start pull loops for each screen
        for screen in self.screen_manager.screens:
            pull_task = asyncio.create_task(self._screen_pull_loop(screen))
            self.pull_tasks[screen.name] = pull_task
            self.tasks.add(pull_task)
        
        print(f"Started scheduler with {len(self.screen_manager.screens)} screens")
    
    async def stop(self):
        """Stop the screen scheduler"""
        if not self.running:
            return
            
        self.running = False
        print("Stopping screen scheduler...")
        
        # Cancel main display task
        if self.display_task:
            self.display_task.cancel()
            try:
                await self.display_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all pull tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for cancellation
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        self.tasks.clear()
        self.pull_tasks.clear()
    
    async def _display_loop(self):
        """Main display rendering loop"""
        frame_time = 1.0 / self.render_fps
        
        while self.running:
            try:
                loop_start = time.monotonic()
                
                # Check if we should rotate screens
                if self.screen_manager.should_rotate_screen():
                    self.screen_manager.rotate_screen()
                
                # Get current screen
                current_screen = self.screen_manager.get_current_screen()
                
                if current_screen:
                    # Clear buffer before rendering
                    buffer = self.display_engine.get_buffer()
                    buffer.fill(0) # Clear with black
                    
                    # Render the screen's plugins into the buffer
                    width, height = self.display_engine.get_dimensions()
                    self.screen_manager.render_screen(
                        current_screen, buffer, width, height)
                    
                    # Always update the display with the (now cleared and possibly rendered) buffer
                    self.display_engine.update()
                
                # Calculate sleep time to maintain target FPS
                loop_time = time.monotonic() - loop_start
                sleep_time = max(0, frame_time - loop_time)
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                print(f"Error in display loop: {e}")
                await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("Received KeyboardInterrupt, shutting down...")
                sys.exit(0)
    
    async def _screen_pull_loop(self, screen):
        """Pull data for all plugins in a screen"""
        last_pull_times = {}  # plugin_name -> last_pull_time
        
        while self.running:
            try:
                current_time = time.monotonic()
                
                # Check each plugin in the screen
                for plugin in screen.get_plugins():
                    if not plugin.enabled:
                        continue
                    
                    plugin_name = plugin.metadata.name
                    last_pull = last_pull_times.get(plugin_name, 0)
                    interval = plugin.metadata.interval
                    
                    # Check if it's time to pull data
                    if (current_time - last_pull) >= interval:
                        if plugin.metadata.refresh_type == "pull":
                            try:
                                # Pull data from plugin
                                data = await plugin.pull()
                                if data:
                                    plugin.data.update(data)
                                    plugin.last_update = current_time
                                    plugin.error_count = 0
                                
                                last_pull_times[plugin_name] = current_time
                                
                            except Exception as e:
                                plugin.error_count += 1
                                print(f"Error pulling data from {plugin_name}: {e}")
                                
                                # Disable plugin if too many errors
                                if plugin.error_count > 5:
                                    plugin.enabled = False
                                    print(f"Disabled plugin {plugin_name} due to errors")
                
                # Memory cleanup
                if len(last_pull_times) > 10:  # Prevent memory leak
                    gc.collect()
                
                # Sleep before next check
                await asyncio.sleep(self.pull_interval)
                
            except Exception as e:
                print(f"Error in screen pull loop for {screen.name}: {e}")
                await asyncio.sleep(5)
    
    def get_status(self):
        """Get scheduler status"""
        current_screen = self.screen_manager.get_current_screen()
        return {
            "running": self.running,
            "render_fps": self.render_fps,
            "current_screen": current_screen.name if current_screen else None,
            "total_screens": len(self.screen_manager.screens),
            "active_pull_tasks": len(self.pull_tasks),
            "screen_manager": self.screen_manager.get_status()
        }
    
    def set_fps(self, fps):
        """Set target rendering FPS"""
        self.render_fps = max(1, min(60, fps))
        print(f"Render FPS set to {self.render_fps}")
    
    def force_screen_rotation(self):
        """Force rotation to next screen"""
        return self.screen_manager.rotate_screen()
