"""
Plugin interface specification for MatrixPortal S3 Dashboard
Defines the standard interface that all plugins must implement
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable

class PluginMetadata:
    """Plugin metadata container"""
    def __init__(self, name: str, version: str, description: str = "",
                 refresh_type: str = "pull", interval: int = 30,
                 default_config: Dict[str, Any] = None):
        self.name = name
        self.version = version
        self.description = description
        self.refresh_type = refresh_type  # "pull" or "push"
        self.interval = interval  # seconds
        self.default_config = default_config or {}

class PluginInterface(ABC):
    """Abstract base class for all dashboard plugins"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.last_update = 0
        self.data = {}
        self.error_count = 0
        
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        pass
    
    async def init(self) -> bool:
        """
        Initialize plugin (optional)
        Returns True if successful, False otherwise
        """
        return True
    
    async def cleanup(self):
        """Clean up plugin resources (optional)"""
        pass
    
    async def pull(self) -> Dict[str, Any]:
        """
        Pull data from external source (for pull-type plugins)
        Returns dictionary of data or raises exception
        """
        if self.metadata.refresh_type == "pull":
            raise NotImplementedError("Pull method must be implemented for pull-type plugins")
        return {}
    
    def push_callback(self, topic: str, payload: Any):
        """
        Handle pushed data (for push-type plugins)
        Called when data is received via MQTT, webhook, etc.
        """
        if self.metadata.refresh_type == "push":
            raise NotImplementedError("Push callback must be implemented for push-type plugins")
    
    @abstractmethod
    def render(self, display_buffer, width: int, height: int) -> bool:
        """
        Render plugin content to display buffer
        
        Args:
            display_buffer: displayio.Bitmap buffer to draw on
            width: buffer width in pixels
            height: buffer height in pixels
            
        Returns:
            True if rendered successfully, False otherwise
        """
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get plugin status information"""
        return {
            "name": self.metadata.name,
            "enabled": self.enabled,
            "last_update": self.last_update,
            "error_count": self.error_count,
            "data_keys": list(self.data.keys()) if self.data else []
        }
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update plugin configuration"""
        self.config.update(new_config)
        self.enabled = self.config.get("enabled", True)

class PluginManager:
    """Manages plugin lifecycle and discovery"""
    
    def __init__(self):
        self.plugins = {}
        self.load_order = []
        
    def discover_plugins(self, plugins_dir: str = "plugins"):
        """Discover plugins in the plugins directory"""
        import os
        
        try:
            plugin_dirs = [d for d in os.listdir(plugins_dir) 
                          if os.path.isdir(f"{plugins_dir}/{d}") and not d.startswith('.')]
            
            for plugin_dir in plugin_dirs:
                try:
                    self._load_plugin(plugins_dir, plugin_dir)
                except Exception as e:
                    print(f"Failed to load plugin {plugin_dir}: {e}")
                    
        except OSError:
            print(f"Plugins directory {plugins_dir} not found")
    
    def _load_plugin(self, plugins_dir: str, plugin_dir: str):
        """Load a single plugin"""
        import importlib
        
        plugin_path = f"{plugins_dir}.{plugin_dir}"
        
        try:
            module = importlib.import_module(plugin_path)
            
            # Look for plugin class
            if hasattr(module, 'Plugin'):
                plugin_class = module.Plugin
                
                # Validate plugin class
                if not issubclass(plugin_class, PluginInterface):
                    raise ValueError(f"Plugin {plugin_dir} does not implement PluginInterface")
                
                # Create plugin instance with default config
                temp_instance = plugin_class({})
                metadata = temp_instance.metadata
                
                # Store plugin info
                self.plugins[metadata.name] = {
                    'class': plugin_class,
                    'module': module,
                    'metadata': metadata,
                    'instance': None
                }
                
                self.load_order.append(metadata.name)
                print(f"Loaded plugin: {metadata.name} v{metadata.version}")
                
            else:
                raise ValueError(f"Plugin {plugin_dir} missing Plugin class")
                
        except ImportError as e:
            raise ValueError(f"Failed to import plugin {plugin_dir}: {e}")
    
    def create_plugin_instance(self, plugin_name: str, config: Dict[str, Any]) -> Optional[PluginInterface]:
        """Create an instance of a plugin with given configuration"""
        if plugin_name not in self.plugins:
            return None
            
        plugin_info = self.plugins[plugin_name]
        
        # Merge default config with provided config
        full_config = plugin_info['metadata'].default_config.copy()
        full_config.update(config)
        
        # Create instance
        instance = plugin_info['class'](full_config)
        plugin_info['instance'] = instance
        
        return instance
    
    def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Get metadata for a plugin"""
        if plugin_name in self.plugins:
            return self.plugins[plugin_name]['metadata']
        return None
    
    def list_plugins(self) -> Dict[str, PluginMetadata]:
        """List all available plugins"""
        return {name: info['metadata'] for name, info in self.plugins.items()}
    
    def get_plugin_instance(self, plugin_name: str) -> Optional[PluginInterface]:
        """Get the current instance of a plugin"""
        if plugin_name in self.plugins:
            return self.plugins[plugin_name]['instance']
        return None
