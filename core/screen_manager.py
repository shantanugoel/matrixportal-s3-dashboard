"""
Screen Manager for MatrixPortal S3 Dashboard
Manages display groups/screens that can contain multiple plugins
"""
import asyncio
import time
import gc

class ScreenLayout:
    """Defines a screen layout with multiple plugin regions"""
    
    def __init__(self, name, plugins_config):
        self.name = name
        self.plugins_config = plugins_config  # List of plugin configs with positions
        self.plugins = []  # Actual plugin instances
        self.enabled = True
        
    def add_plugin(self, plugin_instance):
        """Add a plugin instance to this screen"""
        self.plugins.append(plugin_instance)
    
    def get_plugins(self):
        """Get all plugins in this screen"""
        return self.plugins
    
    def is_enabled(self):
        """Check if this screen is enabled"""
        return self.enabled and len(self.plugins) > 0

class ScreenManager:
    """Manages multiple display screens and rotates between them"""
    
    def __init__(self, config, plugin_manager, network_manager):
        self.config = config
        self.plugin_manager = plugin_manager
        self.network_manager = network_manager
        self.screens = []
        self.current_screen_index = 0
        self.last_rotation = 0
        self.rotation_interval = config.get('rotation_interval', 10)
        
    def load_screens(self):
        """Load screen configurations from config"""
        screens_config = self.config.get('screens', {})
        
        if not screens_config:
            # Fallback: create a default screen with all enabled plugins
            self._create_default_screen()
            return
        
        for screen_name, screen_config in screens_config.items():
            if screen_config.get('enabled', True):
                screen = ScreenLayout(screen_name, screen_config.get('plugins', []))
                
                # Create plugin instances for this screen
                for plugin_config in screen_config.get('plugins', []):
                    plugin_name = plugin_config.get('name')
                    plugin_settings = plugin_config.get('config', {})
                    
                    if plugin_name:
                        # Create plugin instance
                        plugin_instance = self.plugin_manager.create_plugin_instance(
                            plugin_name, plugin_settings)
                        
                        if plugin_instance:
                            # Set network manager for plugins that need it
                            if hasattr(plugin_instance, 'set_network'):
                                plugin_instance.set_network(self.network_manager)
                            
                            # Add position/layout info to plugin
                            plugin_instance.screen_config = plugin_config
                            screen.add_plugin(plugin_instance)
                            print(f"Added plugin {plugin_name} to screen {screen_name}")
                
                if screen.is_enabled():
                    self.screens.append(screen)
                    print(f"Loaded screen: {screen_name} with {len(screen.plugins)} plugins")
        
        if not self.screens:
            self._create_default_screen()
    
    def _create_default_screen(self):
        """Create a default screen with all available plugins"""
        print("Creating default screen with available plugins")
        
        # Get plugins from main config
        plugins_config = self.config.get('plugins', {})
        default_screen = ScreenLayout('default', [])
        
        for plugin_name, plugin_config in plugins_config.items():
            if plugin_config.get('enabled', True):
                plugin_instance = self.plugin_manager.create_plugin_instance(
                    plugin_name, plugin_config)
                
                if plugin_instance:
                    # Set network manager
                    if hasattr(plugin_instance, 'set_network'):
                        plugin_instance.set_network(self.network_manager)
                    
                    # Add default layout info
                    plugin_instance.screen_config = {
                        'name': plugin_name,
                        'position': plugin_config.get('position', 'center'),
                        'height': plugin_config.get('height', 64),
                        'width': plugin_config.get('width', 64),
                        'x': plugin_config.get('x', 0),
                        'y': plugin_config.get('y', 0)
                    }
                    
                    default_screen.add_plugin(plugin_instance)
                    print(f"Added plugin {plugin_name} to default screen")
        
        if default_screen.is_enabled():
            self.screens.append(default_screen)
            print(f"Created default screen with {len(default_screen.plugins)} plugins")
    
    def get_current_screen(self):
        """Get the currently active screen"""
        if not self.screens:
            return None
        return self.screens[self.current_screen_index]
    
    def should_rotate_screen(self):
        """Check if it's time to rotate to the next screen"""
        if len(self.screens) <= 1:
            return False
        
        current_time = time.monotonic()
        return (current_time - self.last_rotation) >= self.rotation_interval
    
    def rotate_screen(self):
        """Rotate to the next screen"""
        if len(self.screens) <= 1:
            return False
        
        self.current_screen_index = (self.current_screen_index + 1) % len(self.screens)
        self.last_rotation = time.monotonic()
        
        current_screen = self.get_current_screen()
        print(f"Rotated to screen: {current_screen.name if current_screen else 'None'}")
        return True
    
    async def pull_screen_data(self, screen):
        """Pull data for all plugins in a screen"""
        if not screen:
            return
        
        pull_tasks = []
        for plugin in screen.get_plugins():
            if hasattr(plugin, 'pull') and plugin.metadata.refresh_type == "pull":
                pull_tasks.append(plugin.pull())
        
        if pull_tasks:
            try:
                # Run all plugin pulls concurrently
                results = await asyncio.gather(*pull_tasks, return_exceptions=True)
                
                # Log any errors
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        plugin_name = screen.plugins[i].metadata.name
                        print(f"Error pulling data for {plugin_name}: {result}")
                
                gc.collect()
            except Exception as e:
                print(f"Error in screen data pull: {e}")
    
    def render_screen(self, screen, display_buffer, width, height):
        """Render all plugins in a screen to the display buffer"""
        if not screen:
            return False
        
        try:
            # Clear the entire buffer first
            for y in range(height):
                for x in range(width):
                    display_buffer[x, y] = 0
            
            # Render each plugin in the screen
            rendered_any = False
            for plugin in screen.get_plugins():
                if plugin.enabled:
                    try:
                        result = plugin.render(display_buffer, width, height)
                        if result:
                            rendered_any = True
                    except Exception as e:
                        print(f"Error rendering plugin {plugin.metadata.name}: {e}")
                        plugin.error_count += 1
            
            return rendered_any
            
        except Exception as e:
            print(f"Error rendering screen {screen.name}: {e}")
            return False
    
    def get_screen_info(self):
        """Get information about all screens"""
        screen_info = []
        for i, screen in enumerate(self.screens):
            plugins_info = []
            for plugin in screen.get_plugins():
                plugins_info.append({
                    'name': plugin.metadata.name,
                    'enabled': plugin.enabled,
                    'position': getattr(plugin, 'screen_config', {}).get('position', 'unknown'),
                    'error_count': plugin.error_count
                })
            
            screen_info.append({
                'name': screen.name,
                'active': i == self.current_screen_index,
                'plugin_count': len(screen.plugins),
                'plugins': plugins_info
            })
        
        return screen_info
    
    def get_status(self):
        """Get screen manager status"""
        current_screen = self.get_current_screen()
        return {
            'total_screens': len(self.screens),
            'current_screen': current_screen.name if current_screen else None,
            'current_screen_index': self.current_screen_index,
            'rotation_interval': self.rotation_interval,
            'time_until_next_rotation': max(0, self.rotation_interval - (time.monotonic() - self.last_rotation)),
            'screens': self.get_screen_info()
        }
