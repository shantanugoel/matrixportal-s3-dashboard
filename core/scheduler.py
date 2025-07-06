"""
Core scheduler for MatrixPortal S3 Dashboard
Manages plugin rotation, timing, and asyncio task coordination
"""
import asyncio
import time
import gc
from .plugin_interface import PluginInterface, PluginManager
import sys

class PluginTask:
    """Represents a scheduled plugin task"""
    def __init__(self, plugin, task_type="pull"):
        self.plugin = plugin
        self.task_type = task_type  # "pull" or "display"
        self.task = None
        self.last_run = 0
        self.next_run = 0
        self.error_count = 0
        
    def should_run(self) -> bool:
        """Check if task should run now"""
        return time.monotonic() >= self.next_run
    
    def schedule_next(self):
        """Schedule next run based on plugin interval"""
        interval = self.plugin.metadata.interval
        self.next_run = time.monotonic() + interval
        self.last_run = time.monotonic()

class DisplayScheduler:
    """Manages display rotation and plugin scheduling"""
    
    def __init__(self, display_engine, plugin_manager):
        self.display_engine = display_engine
        self.plugin_manager = plugin_manager
        self.active_plugins = {}  # name -> PluginTask
        self.current_plugin = None
        self.display_rotation_time = 5  # seconds per plugin
        self.last_rotation = 0
        self.running = False
        
        # Task management
        self.tasks = set()
        self.display_task = None
        
    def add_plugin(self, plugin):
        """Add a plugin to the scheduler"""
        if not plugin.enabled:
            return
            
        metadata = plugin.metadata
        
        # Create pull task if needed
        if metadata.refresh_type == "pull":
            pull_task = PluginTask(plugin, "pull")
            pull_task.schedule_next()
            self.active_plugins[f"{metadata.name}_pull"] = pull_task
            
        # Create display task
        display_task = PluginTask(plugin, "display")
        self.active_plugins[f"{metadata.name}_display"] = display_task
        
        print(f"Added plugin to scheduler: {metadata.name}")
    
    def remove_plugin(self, plugin_name):
        """Remove a plugin from the scheduler"""
        # Remove both pull and display tasks
        for task_name in list(self.active_plugins.keys()):
            if task_name.startswith(plugin_name):
                task = self.active_plugins[task_name]
                if task.task and not task.task.done():
                    task.task.cancel()
                del self.active_plugins[task_name]
        
        # Update current plugin if needed
        if self.current_plugin and self.current_plugin.metadata.name == plugin_name:
            self.current_plugin = None
            
        print(f"Removed plugin from scheduler: {plugin_name}")
    
    def update_plugin_config(self, plugin_name, config):
        """Update plugin configuration"""
        # Find and update plugin
        for task_name, task in self.active_plugins.items():
            if task.plugin.metadata.name == plugin_name:
                task.plugin.update_config(config)
                
                # If disabled, remove from scheduler
                if not task.plugin.enabled:
                    self.remove_plugin(plugin_name)
                    return
                    
                # Reschedule if interval changed
                if task.task_type == "pull":
                    task.schedule_next()
    
    async def start(self):
        """Start the scheduler"""
        if self.running:
            return
            
        self.running = True
        print("Starting display scheduler...")
        
        # Start main scheduler task
        self.display_task = asyncio.create_task(self._main_loop())
        
        # Start individual plugin tasks
        for task_name, plugin_task in self.active_plugins.items():
            if plugin_task.task_type == "pull":
                plugin_task.task = asyncio.create_task(
                    self._pull_task_loop(plugin_task)
                )
                self.tasks.add(plugin_task.task)
    
    async def stop(self):
        """Stop the scheduler"""
        if not self.running:
            return
            
        self.running = False
        print("Stopping display scheduler...")
        
        # Cancel main display task
        if self.display_task:
            self.display_task.cancel()
            try:
                await self.display_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all plugin tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for cancellation
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        self.tasks.clear()
    
    async def _main_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                # Check if we need to rotate display
                if self._should_rotate_display():
                    await self._rotate_display()
                
                # Render current plugin
                if self.current_plugin:
                    await self._render_current_plugin()
                
                # Brief yield to other tasks
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Error in scheduler main loop: {e}")
                await asyncio.sleep(1)

            except KeyboardInterrupt:
                print("Received KeyboardInterrupt, shutting down...")
                await self.stop()
                sys.exit(0)
    
    def _should_rotate_display(self) -> bool:
        """Check if it's time to rotate to next plugin"""
        if not self.current_plugin:
            return True
            
        return (time.monotonic() - self.last_rotation) >= self.display_rotation_time
    
    async def _rotate_display(self):
        """Rotate to next plugin"""
        # Get list of enabled display plugins
        display_plugins = []
        for task_name, task in self.active_plugins.items():
            if task.task_type == "display" and task.plugin.enabled:
                display_plugins.append(task.plugin)
        
        if not display_plugins:
            self.current_plugin = None
            return
        
        # Find next plugin
        if self.current_plugin:
            try:
                current_index = display_plugins.index(self.current_plugin)
                next_index = (current_index + 1) % len(display_plugins)
            except ValueError:
                next_index = 0
        else:
            next_index = 0
        
        # Switch to next plugin
        self.current_plugin = display_plugins[next_index]
        self.last_rotation = time.monotonic()
        
        print(f"Rotated to plugin: {self.current_plugin.metadata.name}")
        
        # Clear display for smooth transition
        self.display_engine.clear()
    
    async def _render_current_plugin(self):
        """Render the current plugin to display"""
        if not self.current_plugin:
            return
            
        try:
            # Get display buffer
            buffer = self.display_engine.get_buffer()
            width, height = self.display_engine.get_dimensions()
            
            # Render plugin
            success = self.current_plugin.render(buffer, width, height)
            
            if success:
                # Update display
                self.display_engine.update()
            else:
                print(f"Plugin {self.current_plugin.metadata.name} render failed")
                
        except Exception as e:
            print(f"Error rendering plugin {self.current_plugin.metadata.name}: {e}")
    
    async def _pull_task_loop(self, plugin_task: PluginTask):
        """Loop for handling pull-based plugin data updates"""
        while self.running:
            try:
                if plugin_task.should_run() and plugin_task.plugin.enabled:
                    # Pull data from plugin
                    try:
                        data = await plugin_task.plugin.pull()
                        plugin_task.plugin.data.update(data)
                        plugin_task.plugin.last_update = time.monotonic()
                        plugin_task.error_count = 0
                        
                    except Exception as e:
                        plugin_task.error_count += 1
                        print(f"Error pulling data from {plugin_task.plugin.metadata.name}: {e}")
                        
                        # Disable plugin if too many errors
                        if plugin_task.error_count > 5:
                            plugin_task.plugin.enabled = False
                            print(f"Disabled plugin {plugin_task.plugin.metadata.name} due to errors")
                    
                    # Schedule next run
                    plugin_task.schedule_next()
                
                # Sleep until next check
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Error in pull task loop for {plugin_task.plugin.metadata.name}: {e}")
                await asyncio.sleep(5)
    
    def get_status(self):
        """Get scheduler status"""
        return {
            "running": self.running,
            "active_plugins": len(self.active_plugins),
            "current_plugin": self.current_plugin.metadata.name if self.current_plugin else None,
            "display_rotation_time": self.display_rotation_time,
            "last_rotation": self.last_rotation,
            "tasks": len(self.tasks)
        }
    
    def set_rotation_time(self, seconds):
        """Set display rotation time"""
        self.display_rotation_time = max(1, seconds)
        print(f"Display rotation time set to {self.display_rotation_time} seconds")
    
    def force_rotation(self):
        """Force rotation to next plugin"""
        self.last_rotation = 0
