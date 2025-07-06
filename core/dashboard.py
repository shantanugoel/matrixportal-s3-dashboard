"""
Main dashboard controller for MatrixPortal S3 Dashboard
Coordinates all system components and manages the overall application lifecycle
"""
import asyncio
import time
import gc
import sys
from .display import DisplayEngine
from .scheduler import DisplayScheduler
from .plugin_interface import PluginManager
from .config import ConfigManager
from .simple_webserver import WebServer
from .network import NetworkManager

class Dashboard:
    """Main dashboard application controller"""
    
    def __init__(self):
        self.running = False
        
        # Core components
        self.config_manager = None
        self.network_manager = None
        self.plugin_manager = None
        self.display_engine = None
        self.scheduler = None
        self.web_server = None
        
        # Configuration
        self.config = {}
        
        # Initialize components
        self._init_components()
    
    def _init_components(self):
        """Initialize all dashboard components"""
        print("Initializing dashboard components...")
        
        try:
            # Configuration manager
            self.config_manager = ConfigManager()
            self.config = self.config_manager.load_config()
            
            # Network manager - merge network and system config for WiFi credentials
            network_config = self.config.get('network', {}).copy()
            system_config = self.config.get('system', {})
            network_config['ssid'] = system_config.get('wifi_ssid', '')
            network_config['password'] = system_config.get('wifi_password', '')
            self.network_manager = NetworkManager(network_config)
            
            # Plugin manager
            self.plugin_manager = PluginManager()
            self.plugin_manager.discover_plugins()
            
            # Display engine
            display_config = self.config.get('display', {})
            self.display_engine = DisplayEngine(
                width=display_config.get('width', 64),
                height=display_config.get('height', 64),
                bit_depth=display_config.get('bit_depth', 6)
            )
            
            # Scheduler
            self.scheduler = DisplayScheduler(self.display_engine, self.plugin_manager)
            
            # Web server
            web_config = self.config.get('web', {})
            self.web_server = WebServer(
                port=web_config.get('port', 80),
                config_manager=self.config_manager,
                plugin_manager=self.plugin_manager,
                scheduler=self.scheduler
            )
            
            print("Dashboard components initialized successfully")
            
        except Exception as e:
            print(f"Component initialization error: {e}")
            raise
    
    def run(self):
        """Run the dashboard application"""
        print("Starting dashboard...")
        
        try:
            # Start the asyncio event loop
            asyncio.run(self._main_loop())
            
        except KeyboardInterrupt:
            print("Dashboard interrupted by user")
            sys.exit(0)
            
        except Exception as e:
            print(f"Dashboard error: {e}")
            raise
        
        finally:
            print("Dashboard stopped")
    
    async def _main_loop(self):
        """Main application loop"""
        self.running = True
        
        try:
            # Initialize network connection
            await self._init_network()
            
            # Load and configure plugins
            await self._init_plugins()
            
            # Start core services
            await self._start_services()
            
            # Main application loop
            while self.running:
                await self._update_loop()
                await asyncio.sleep(0.1)
                
        except Exception as e:
            print(f"Main loop error: {e}")
            raise

        except KeyboardInterrupt:
            print("Main loop interrupted by user")
        
        finally:
            await self._cleanup()
    
    async def _init_network(self):
        """Initialize network connection"""
        print("Initializing network...")
        
        try:
            connected = await self.network_manager.connect()
            if not connected:
                print("Network connection failed")
                # Continue without network for offline operation
            else:
                print("Network connected successfully")
                
        except Exception as e:
            print(f"Network initialization error: {e}")
    
    async def _init_plugins(self):
        """Initialize and configure plugins"""
        print("Initializing plugins...")
        
        plugin_configs = self.config.get('plugins', {})
        
        for plugin_name, plugin_config in plugin_configs.items():
            try:
                if plugin_config.get('enabled', False):
                    # Create plugin instance
                    plugin = self.plugin_manager.create_plugin_instance(plugin_name, plugin_config)
                    
                    if plugin:
                        # Initialize plugin
                        await plugin.init()
                        
                        # Add to scheduler
                        self.scheduler.add_plugin(plugin)
                        
                        print(f"Initialized plugin: {plugin_name}")
                    else:
                        print(f"Failed to create plugin: {plugin_name}")
                        
            except Exception as e:
                print(f"Plugin initialization error ({plugin_name}): {e}")
    
    async def _start_services(self):
        """Start core services"""
        print("Starting core services...")
        
        try:
            # Start scheduler
            await self.scheduler.start()
            
            # Start web server
            if self.network_manager.is_connected():
                await self.web_server.start()
            
            print("Core services started")
            
        except Exception as e:
            print(f"Service startup error: {e}")
            raise
    
    async def _update_loop(self):
        """Main update loop"""
        # Poll web server for incoming requests
        if self.web_server:
            self.web_server.poll()
        
        # Periodic tasks
        await self._periodic_tasks()
        
        # Memory management
        if time.monotonic() % 30 < 0.1:  # Every 30 seconds
            gc.collect()
    
    async def _periodic_tasks(self):
        """Handle periodic maintenance tasks"""
        # Check network connectivity
        if not self.network_manager.is_connected():
            try:
                await self.network_manager.reconnect()
            except:
                pass
        
        # Update display brightness based on time
        self._update_display_brightness()
    
    def _update_display_brightness(self):
        """Update display brightness based on configuration or time"""
        brightness_config = self.config.get('display', {}).get('brightness', {})
        
        if brightness_config.get('auto', False):
            # Auto brightness based on time
            import time
            current_time = time.localtime()
            hour = current_time.tm_hour
            
            if 22 <= hour or hour <= 6:  # Night time
                brightness = brightness_config.get('night', 0.2)
            else:  # Day time
                brightness = brightness_config.get('day', 0.8)
        else:
            brightness = brightness_config.get('manual', 0.5)
        
        self.display_engine.set_brightness(brightness)
    
    async def _cleanup(self):
        """Clean up resources"""
        print("Cleaning up dashboard...")
        
        try:
            # Stop services
            if self.scheduler:
                await self.scheduler.stop()
                
            if self.web_server:
                await self.web_server.stop()
            
            # Clean up components
            if self.display_engine:
                self.display_engine.cleanup()
                
            if self.network_manager:
                await self.network_manager.disconnect()
            
            # Force garbage collection
            gc.collect()
            
            print("Dashboard cleanup completed")
            
        except Exception as e:
            print(f"Cleanup error: {e}")
    
    def cleanup(self):
        """Synchronous cleanup method"""
        try:
            if self.display_engine:
                self.display_engine.cleanup()
            gc.collect()
        except Exception as e:
            print(f"Sync cleanup error: {e}")
    
    def stop(self):
        """Stop the dashboard"""
        self.running = False
    
    def get_status(self):
        """Get dashboard status"""
        return {
            'running': self.running,
            'network': self.network_manager.get_status() if self.network_manager else {},
            'scheduler': self.scheduler.get_status() if self.scheduler else {},
            'plugins': len(self.plugin_manager.plugins) if self.plugin_manager else 0,
            'memory': gc.mem_free()
        }
