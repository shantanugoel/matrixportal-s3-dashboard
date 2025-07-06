# MatrixPortal S3 Dashboard - Agent Configuration

## Project Overview

This is a modular dashboard system for Adafruit MatrixPortal S3 with 64x64 RGB LED matrix, built in CircuitPython. The system displays rotating content through a plugin-based architecture.

## Development Commands

### Code Validation
- **Syntax Check**: `python -m py_compile code.py`
- **Lint Check**: All files compile successfully with Python 3.x
- **Import Validation**: Static analysis passes (CircuitPython-specific imports expected to fail)

### Hardware Testing
- **Deploy**: Copy all files to CIRCUITPY drive when MatrixPortal S3 is connected
- **Monitor**: Use serial console to view output and debug messages
- **Web Interface**: Access `http://<device-ip>` when connected to WiFi

## Code Architecture

### Core Components
- `boot.py` - Hardware initialization (PSRAM, SD card, safe mode)
- `code.py` - Main entry point with error handling and restart logic
- `core/dashboard.py` - Central controller coordinating all components
- `core/scheduler.py` - AsyncIO-based plugin rotation and timing
- `core/display.py` - RGB LED matrix display with double buffering
- `core/simple_webserver.py` - Web configuration interface
- `core/network.py` - WiFi connectivity and network management
- `core/config.py` - Configuration management with atomic writes
- `core/plugin_interface.py` - Plugin system base classes and manager

### Plugin System
- Location: `plugins/<plugin_name>/__init__.py`
- Base class: `PluginInterface`
- Required: `metadata` property and `render()` method
- Optional: `init()`, `pull()`, `push_callback()` methods
- Example: `plugins/clock/` - Digital clock with customizable format

## CircuitPython Compatibility

### Modules Used
- `wifi` - WiFi radio control
- `socketpool` - Network socket operations
- `displayio` - RGB matrix display control
- `rgbmatrix` - LED matrix hardware interface
- `supervisor` - System control and monitoring
- `microcontroller` - Hardware access and reset
- `watchdog` - System reliability
- `asyncio` - Cooperative multitasking
- `gc` - Garbage collection
- `time` - Time and monotonic clock
- `json` - Configuration serialization
- `os` - File system operations

### Key Differences from Standard Python
- No `typing` module - all type hints removed
- No `socket` module - uses `socketpool` instead
- No `os.path` - uses try/except for file existence checks
- No `importlib` - uses `__import__` for dynamic imports
- Limited `os.stat` - file size at index 6
- Manual memory management with `gc.collect()`

## Configuration

### WiFi Setup
- **Secure Method (Recommended)**: 
  - Copy `settings.toml.template` to `settings.toml`
  - Fill in your actual WiFi credentials in `settings.toml`
  - `config.json` uses environment variables: `${WIFI_SSID}` and `${WIFI_PASSWORD}`
- **Direct Method**: Edit `config.json` directly (not recommended for version control)
- **Web Interface**: Use web interface to update settings
- Device will start captive portal if connection fails

### Display Settings
- `display.width/height` - Matrix dimensions (default: 64x64)
- `display.bit_depth` - Color depth (default: 6)
- `display.brightness` - Manual/auto brightness control
- `system.rotation_interval` - Plugin display time in seconds

### Plugin Configuration
- Each plugin has its own config section in `config.json`
- `enabled` - Enable/disable plugin
- Plugin-specific settings (intervals, API keys, etc.)

## Plugin Development

### Creating a New Plugin
1. Create directory: `plugins/<name>/`
2. Create `__init__.py` with `Plugin` class
3. Inherit from `PluginInterface`
4. Implement required methods:
   - `metadata` property returning `PluginMetadata`
   - `render(display_buffer, width, height)` method
5. Optional methods for data fetching:
   - `async pull()` for periodic data updates
   - `push_callback(topic, payload)` for real-time data

### Plugin Template
```python
from core.plugin_interface import PluginInterface, PluginMetadata

class Plugin(PluginInterface):
    @property
    def metadata(self):
        return PluginMetadata(
            name="my_plugin",
            version="1.0.0",
            description="My custom plugin",
            refresh_type="pull",  # or "push"
            interval=30,  # seconds
            default_config={"enabled": True}
        )
    
    async def pull(self):
        # Fetch data
        return {"data": "value"}
    
    def render(self, display_buffer, width, height):
        # Draw to display_buffer
        # Use display_buffer[x, y] = color_index
        return True
```

## Memory Management

### Optimization Strategies
- Pre-allocate buffers in PSRAM when available
- Use `gc.collect()` periodically
- Minimize string concatenation in render loops
- Reuse objects instead of creating new ones
- Keep plugin data structures small

### Memory Monitoring
- Check `gc.mem_free()` in web interface
- Monitor for heap fragmentation
- Use simple data structures in plugins
- Avoid large temporary objects

## Network Architecture

### Web Server
- Simple HTTP server on port 80
- Serves configuration interface
- REST API endpoints:
  - `GET /` - Configuration web page
  - `GET /api/status` - System status
  - `GET /api/config` - Current configuration
  - `GET /api/plugins` - Plugin information
  - `POST /api/config` - Update configuration

### Network Reliability
- Automatic WiFi reconnection
- Connection quality monitoring
- Exponential backoff on failures
- Watchdog timer for system recovery

## Testing Guidelines

### Static Testing (Desktop)
- All Python files should compile successfully
- Import errors for CircuitPython modules are expected
- Use `python -m py_compile <file>` for syntax validation

### Hardware Testing (MatrixPortal S3)
- Copy files to CIRCUITPY drive
- Monitor serial output for errors
- Check web interface accessibility
- Verify plugin rotation and display updates
- Test configuration changes via web interface

### Plugin Testing
- Create simple test plugins first
- Verify plugin discovery and loading
- Test render loop performance
- Check memory usage during operation
- Validate configuration handling

## Troubleshooting

### Common Issues
- **Import errors**: Normal for CircuitPython-specific modules on desktop
- **Memory errors**: Reduce plugin complexity, add gc.collect() calls
- **WiFi connection**: Check credentials, signal strength, network compatibility
- **Display issues**: Verify matrix wiring, power supply, bit depth settings
- **Plugin loading**: Check syntax, inheritance, required methods

### Debug Tools
- Serial console output for error messages
- Web interface status page for system health
- Memory usage monitoring
- Network connectivity status
- Plugin error counters

## Performance Considerations

### Display Refresh
- Target 60fps for smooth animation
- Use double buffering to prevent flicker
- Manual refresh control during network operations
- Optimize render loops for speed

### AsyncIO Usage
- Keep awaitable sections under 10ms
- Use proper async/await patterns
- Yield control frequently in long operations
- Monitor task scheduling and timing

### Plugin Efficiency
- Minimize network requests
- Cache data when possible
- Use efficient drawing algorithms
- Profile render performance

## Future Enhancements

### Planned Features
- OTA updates via WebDAV
- BLE configuration interface
- Plugin marketplace integration
- Advanced animation support
- Real-time collaboration features
- Voice control integration
- Mobile app companion

### Extension Points
- Additional display effects
- More data source integrations
- Advanced scheduling options
- User interface improvements
- Performance optimizations
- Power management features
