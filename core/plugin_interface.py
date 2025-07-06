"""
Plugin interface specification for MatrixPortal S3 Dashboard
Defines the standard interface that all plugins must implement
"""
import asyncio

class PluginMetadata:
    """Plugin metadata container"""
    def __init__(self, name, version, description="",
                 refresh_type="pull", interval=30,
                 default_config=None):
        self.name = name
        self.version = version
        self.description = description
        self.refresh_type = refresh_type  # "pull" or "push"
        self.interval = interval  # seconds
        self.default_config = default_config or {}

class PluginInterface:
    """Base class for all dashboard plugins"""
    
    def __init__(self, config):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.last_update = 0
        self.data = {}
        self.error_count = 0
        self.network = None
        
    @property
    def metadata(self):
        """Return plugin metadata - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement metadata property")
    
    async def init(self):
        """
        Initialize plugin (optional)
        Returns True if successful, False otherwise
        """
        return True
    
    async def cleanup(self):
        """Clean up plugin resources (optional)"""
        pass
    
    def set_network(self, network_manager):
        """Set the network manager for plugins that need network access"""
        self.network = network_manager
    
    async def pull(self):
        """
        Pull data from external source (for pull-type plugins)
        Returns dictionary of data or raises exception
        """
        if self.metadata.refresh_type == "pull":
            raise NotImplementedError("Pull method must be implemented for pull-type plugins")
        return {}
    
    def push_callback(self, topic, payload):
        """
        Handle pushed data (for push-type plugins)
        Called when data is received via MQTT, webhook, etc.
        """
        if self.metadata.refresh_type == "push":
            raise NotImplementedError("Push callback must be implemented for push-type plugins")
    
    def render(self, display_buffer, width, height):
        """
        Render plugin content to display buffer
        
        Args:
            display_buffer: displayio.Bitmap buffer to draw on
            width: buffer width in pixels
            height: buffer height in pixels
            
        Returns:
            True if rendered successfully, False otherwise
        """
        raise NotImplementedError("Subclasses must implement render method")
    
    def get_status(self):
        """Get plugin status information"""
        return {
            "name": self.metadata.name,
            "enabled": self.enabled,
            "last_update": self.last_update,
            "error_count": self.error_count,
            "data_keys": list(self.data.keys()) if self.data else []
        }
    
    def update_config(self, new_config):
        """Update plugin configuration"""
        self.config.update(new_config)
        self.enabled = self.config.get("enabled", True)

class PluginManager:
    """Manages plugin lifecycle and discovery"""
    
    def __init__(self):
        self.plugins = {}
        self.load_order = []
        
    def discover_plugins(self, plugins_dir="plugins"):
        """Discover plugins in the plugins directory"""
        import os
        
        try:
            # Get all directory entries
            all_entries = os.listdir(plugins_dir)
            plugin_dirs = []
            
            print(f"Found entries in {plugins_dir}: {all_entries}")
            
            # Filter for directories (not files)
            for d in all_entries:
                if not d.startswith('.'):
                    try:
                        # Try to list the directory to see if it's a directory
                        os.listdir(f"{plugins_dir}/{d}")
                        plugin_dirs.append(d)
                        print(f"Found plugin directory: {d}")
                    except OSError:
                        # Not a directory, skip
                        print(f"Skipping non-directory: {d}")
                        pass
            
            for plugin_dir in plugin_dirs:
                try:
                    self._load_plugin(plugins_dir, plugin_dir)
                except Exception as e:
                    print(f"Failed to load plugin {plugin_dir}: {e}")
                    
        except OSError:
            print(f"Plugins directory {plugins_dir} not found")
    
    def _load_plugin(self, plugins_dir, plugin_dir):
        """Load a single plugin"""
        plugin_path = f"{plugins_dir}.{plugin_dir}"
        
        try:
            print(f"Importing plugin module: {plugin_path}")
            # In CircuitPython, try different import approaches
            try:
                # Try simple __import__ first
                module = __import__(plugin_path)
                # Navigate to the submodule
                for part in plugin_path.split('.')[1:]:
                    module = getattr(module, part)
                print(f"Successfully imported module with simple __import__")
            except Exception as e1:
                print(f"Simple __import__ failed: {e1}")
                try:
                    # Try with fromlist
                    module = __import__(plugin_path, fromlist=[plugin_dir])
                    print(f"Successfully imported module with fromlist")
                except Exception as e2:
                    print(f"Import with fromlist failed: {e2}")
                    raise e2
            
            # Look for plugin class
            if hasattr(module, 'Plugin'):
                plugin_class = module.Plugin
                print(f"Found Plugin class")
                
                # Validate plugin class
                print(f"Checking if subclass of PluginInterface")
                if not issubclass(plugin_class, PluginInterface):
                    raise ValueError(f"Plugin {plugin_dir} does not implement PluginInterface")
                print(f"Subclass check passed")
                
                # Create plugin instance with default config
                print(f"Creating temp instance")
                temp_instance = plugin_class({})
                print(f"Getting metadata")
                metadata = temp_instance.metadata
                print(f"Got metadata: {metadata.name}")
                
                # Store plugin info
                self.plugins[metadata.name] = {
                    'class': plugin_class,
                    'module': module,
                    'metadata': metadata,
                    'instance': None
                }
                
                self.load_order.append(metadata.name)
                print(f"Loaded plugin: {metadata.name} v{metadata.version}")
                print(f"Total plugins loaded: {list(self.plugins.keys())}")
                
            else:
                raise ValueError(f"Plugin {plugin_dir} missing Plugin class")
                
        except ImportError as e:
            raise ValueError(f"Failed to import plugin {plugin_dir}: {e}")
    
    def create_plugin_instance(self, plugin_name, config):
        """Create an instance of a plugin with given configuration"""
        print(f"Attempting to create plugin: {plugin_name}")
        print(f"Available plugins: {list(self.plugins.keys())}")
        
        if plugin_name not in self.plugins:
            print(f"Plugin {plugin_name} not found in available plugins")
            return None
            
        plugin_info = self.plugins[plugin_name]
        
        # Merge default config with provided config
        full_config = plugin_info['metadata'].default_config.copy()
        full_config.update(config)
        
        # Create instance
        instance = plugin_info['class'](full_config)
        plugin_info['instance'] = instance
        
        return instance
    
    def get_plugin_metadata(self, plugin_name):
        """Get metadata for a plugin"""
        if plugin_name in self.plugins:
            return self.plugins[plugin_name]['metadata']
        return None
    
    def list_plugins(self):
        """List all available plugins"""
        return {name: info['metadata'] for name, info in self.plugins.items()}
    
    def get_plugin_instance(self, plugin_name):
        """Get the current instance of a plugin"""
        if plugin_name in self.plugins:
            return self.plugins[plugin_name]['instance']
        return None
    
    def reload_plugins(self):
        """Reload all plugins (for configuration changes)"""
        print("Reloading plugins after configuration change")
        # For now, just log the reload - full reload would require scheduler coordination
        # In a full implementation, this would:
        # 1. Stop all plugin tasks
        # 2. Recreate instances with new config
        # 3. Restart tasks
        return True
