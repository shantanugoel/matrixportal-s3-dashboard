# MatrixPortal S3 Dashboard

A modular, plugin-based dashboard system for the Adafruit MatrixPortal S3 with 64×64 RGB LED matrix, built in CircuitPython. Display rotating content including clocks, weather, sports scores, and more through a sophisticated plugin architecture.

![MatrixPortal S3 Dashboard](https://img.shields.io/badge/Platform-CircuitPython-blue) ![License](https://img.shields.io/badge/License-MIT-green) ![Hardware](https://img.shields.io/badge/Hardware-MatrixPortal%20S3-red)

## ✨ Features

### 🔌 Plugin System
- **Modular Architecture**: Easy-to-develop plugins with standardized interface
- **Hot Configuration**: Enable/disable plugins through web interface
- **Auto-Discovery**: Plugins automatically detected and loaded
- **Error Isolation**: Plugin failures don't crash the system

### 🌐 Network & Reliability
- **WiFi Management**: Automatic connection with exponential backoff retry
- **NTP Time Sync**: Accurate time synchronization with configurable servers
- **Captive Portal**: Fallback setup mode when WiFi fails
- **Watchdog Protection**: System reliability with automatic recovery
- **Web Configuration**: Full-featured web interface for remote management

### 🕐 Built-in Clock Plugin
- **Accurate Time**: NTP synchronization with timezone support
- **Custom Display**: Hand-crafted 5×7 pixel font for LED matrix
- **Flexible Format**: 12/24 hour modes with optional seconds
- **Timezone Support**: Direct UTC offset configuration (e.g., +5.5 for IST)

### 📱 Web Interface
- **Real-time Status**: System health, network info, memory usage
- **Configuration Forms**: Easy plugin and system configuration
- **Mobile Friendly**: Responsive design works on phones and tablets
- **API Access**: RESTful endpoints for advanced integration

## 🛠️ Hardware Requirements

### Required Components
- **[Adafruit MatrixPortal S3](https://www.adafruit.com/product/5778)** - ESP32-S3 based controller
- **[64×64 P3 RGB LED Matrix](https://www.waveshare.com/64x64-rgb-led-matrix.htm)** - P3 pitch, HUB75 interface
- **5V Power Supply** - 4A+ recommended for full brightness
- **MicroSD Card** - Optional, for data caching and larger assets

### Optional Components
- **Enclosure/Frame** - For mounting the LED matrix
- **Level Shifters** - If using non-P3 matrices
- **Temperature Sensor** - For brightness auto-adjustment

## 🚀 Quick Start

### 1. Hardware Setup
```
MatrixPortal S3 → LED Matrix (via HUB75 connector)
Power Supply (5V) → LED Matrix power terminals
USB-C → MatrixPortal S3 (for programming)
```

### 2. Software Installation

1. **Install CircuitPython** on MatrixPortal S3:
   - Download [CircuitPython 9.x](https://circuitpython.org/board/adafruit_matrixportal_s3/)
   - Flash to device following [Adafruit's guide](https://learn.adafruit.com/welcome-to-circuitpython)

2. **Install Required Libraries**:
   ```bash
   # Download the CircuitPython Library Bundle
   # Copy these libraries to /lib/ on the device:
   - adafruit_matrixportal
   - adafruit_requests
   - adafruit_ntp
   - adafruit_httpserver
   - displayio
   - asyncio
   ```

3. **Deploy Dashboard Code**:
   ```bash
   git clone https://github.com/yourusername/matrixportal-s3-dashboard.git
   cd matrixportal-s3-dashboard
   
   # Copy all files to your MatrixPortal S3 (CIRCUITPY drive)
   cp -r * /Volumes/CIRCUITPY/  # macOS/Linux
   # or
   robocopy . E:\ /E  # Windows
   ```

### 3. Configuration

1. **WiFi Setup** (Choose one method):

   **Method A - Environment Variables (Recommended)**:
   ```bash
   # Copy template and edit with your credentials
   cp settings.toml.template settings.toml
   # Edit settings.toml with your WiFi details
   ```

   **Method B - Direct Configuration**:
   ```json
   // Edit config.json
   {
     "system": {
       "wifi_ssid": "YourWiFiName",
       "wifi_password": "YourPassword"
     }
   }
   ```

2. **First Boot**:
   - Device will attempt WiFi connection
   - Check serial console for IP address
   - Access web interface at `http://device-ip`

## ⚙️ Configuration

### Web Interface
Access the dashboard through your browser:
```
http://[device-ip]/
```

Features:
- **System Status**: Network, memory, plugin status
- **Plugin Configuration**: Enable/disable and configure plugins
- **Network Settings**: WiFi credentials and connection management
- **Display Settings**: Brightness, rotation timing

### Configuration Files

#### `config.json` - Main Configuration
```json
{
  "system": {
    "wifi_ssid": "${WIFI_SSID}",
    "wifi_password": "${WIFI_PASSWORD}",
    "display_brightness": 50,
    "rotation_interval": 5
  },
  "plugins": {
    "clock": {
      "enabled": true,
      "utc_offset_hours": 5.5,
      "timezone_name": "IST",
      "ntp_enabled": true,
      "format_24h": true
    }
  }
}
```

#### `settings.toml` - Secure Credentials
```toml
WIFI_SSID="YourNetworkName"
WIFI_PASSWORD="YourNetworkPassword"
```

### Clock Plugin Configuration
```json
{
  "clock": {
    "enabled": true,
    "format_24h": true,           // 24-hour vs 12-hour format
    "display_seconds": false,     // Show seconds
    "utc_offset_hours": 5.5,     // Timezone offset (IST = +5.5)
    "timezone_name": "IST",      // Display name
    "ntp_enabled": true,         // NTP time sync
    "ntp_server": "pool.ntp.org", // NTP server
    "ntp_sync_interval": 3600    // Sync every hour
  }
}
```

## 🔌 Plugin Development

### Creating a New Plugin

1. **Create Plugin Directory**:
   ```bash
   mkdir plugins/myplugin
   ```

2. **Implement Plugin Class**:
   ```python
   # plugins/myplugin/__init__.py
   from core.plugin_interface import PluginInterface, PluginMetadata
   
   class Plugin(PluginInterface):
       @property
       def metadata(self):
           return PluginMetadata(
               name="myplugin",
               version="1.0.0",
               description="My custom plugin",
               refresh_type="pull",  # or "push"
               interval=30,  # seconds
               default_config={"enabled": True}
           )
       
       async def pull(self):
           """Fetch data (for pull-type plugins)"""
           return {"data": "Hello World"}
       
       def render(self, display_buffer, width, height):
           """Render to LED matrix"""
           # Draw to display_buffer[x, y] = color_index
           for x in range(width):
               for y in range(height):
                   display_buffer[x, y] = 1 if (x + y) % 2 else 0
           return True
   ```

3. **Add Configuration**:
   ```json
   // Add to config.json
   {
     "plugins": {
       "myplugin": {
         "enabled": true,
         "custom_setting": "value"
       }
     }
   }
   ```

### Plugin Interface Reference

#### Required Methods
- `metadata` - Plugin information and configuration
- `render(display_buffer, width, height)` - Draw content to matrix

#### Optional Methods
- `async init()` - Initialize plugin resources
- `async pull()` - Fetch data (for pull-type plugins)
- `push_callback(topic, payload)` - Handle pushed data
- `async cleanup()` - Clean up resources

#### Plugin Types
- **Pull**: Periodically fetch data (weather, APIs, etc.)
- **Push**: Receive real-time data (MQTT, webhooks, etc.)

## 🏗️ Development Setup

### Requirements
- Python 3.8+ (for desktop testing)
- CircuitPython 9.x (for device)
- Git

### Development Workflow

1. **Clone Repository**:
   ```bash
   git clone https://github.com/yourusername/matrixportal-s3-dashboard.git
   cd matrixportal-s3-dashboard
   ```

2. **Desktop Testing**:
   ```bash
   # Syntax checking
   python -m py_compile code.py
   python -m py_compile core/*.py
   python -m py_compile plugins/*/__init__.py
   ```

3. **Deploy to Device**:
   ```bash
   # Copy files to MatrixPortal S3
   cp -r * /Volumes/CIRCUITPY/
   ```

4. **Monitor & Debug**:
   ```bash
   # Monitor serial output
   screen /dev/tty.usbmodem* 115200
   # or use the Mu editor for easier debugging
   ```

### Project Structure
```
matrixportal-s3-dashboard/
├── code.py                 # Main entry point
├── boot.py                 # Hardware initialization
├── config.json             # System configuration
├── settings.toml           # WiFi credentials
├── core/                   # Core system modules
│   ├── dashboard.py        # Main controller
│   ├── scheduler.py        # Plugin rotation
│   ├── display.py          # LED matrix control
│   ├── network.py          # WiFi & NTP management
│   ├── config.py           # Configuration management
│   ├── simple_webserver.py # Web interface
│   └── plugin_interface.py # Plugin system
├── plugins/                # Plugin directory
│   └── clock/              # Built-in clock plugin
│       └── __init__.py
└── lib/                    # CircuitPython libraries
```

## 🐛 Troubleshooting

### Common Issues

#### "Failed to fetch" in Web Interface
- **Cause**: Device filesystem is read-only (USB connected)
- **Solution**: Disconnect USB cable, restart device, connect via WiFi

#### Display Not Working
- **Check**: Power supply (5V, 4A+)
- **Check**: HUB75 cable connection
- **Check**: Display configuration in config.json

#### WiFi Connection Failed
- **Check**: Credentials in settings.toml
- **Check**: Network compatibility (2.4GHz required)
- **Try**: Captive portal mode (access point fallback)

#### Time Showing Incorrectly
- **Check**: UTC offset in clock plugin config
- **Check**: NTP server accessibility
- **Try**: Manual time sync via web interface

### Debug Commands

```python
# In REPL (Ctrl+C to interrupt, then):
import gc
print(f"Free memory: {gc.mem_free()}")

import wifi
print(f"WiFi connected: {wifi.radio.connected}")
print(f"IP address: {wifi.radio.ipv4_address}")

# Check plugin status
from core.plugin_interface import PluginManager
pm = PluginManager()
pm.discover_plugins()
print(f"Plugins found: {list(pm.plugins.keys())}")
```

### Memory Optimization
- Use `gc.collect()` regularly
- Keep plugin data structures small
- Pre-allocate buffers when possible
- Monitor memory usage via web interface

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Guidelines
- Follow Python/CircuitPython best practices
- Test on actual hardware before submitting
- Include documentation for new features
- Maintain compatibility with CircuitPython 9.x

### Plugin Contributions
- Create plugins in separate directories
- Include clear documentation and examples
- Follow the plugin interface specification
- Test error handling and edge cases

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[Adafruit](https://adafruit.com)** - For the amazing MatrixPortal S3 hardware and CircuitPython
- **[CircuitPython Community](https://circuitpython.org)** - For the excellent libraries and documentation
- **Contributors** - Everyone who has contributed code, ideas, and feedback

## 📚 Resources

### Documentation
- [CircuitPython Documentation](https://docs.circuitpython.org/)
- [MatrixPortal S3 Guide](https://learn.adafruit.com/adafruit-matrixportal-s3)
- [RGB Matrix Guide](https://learn.adafruit.com/32x16-32x32-rgb-led-matrix)

### Hardware
- [Adafruit MatrixPortal S3](https://www.adafruit.com/product/5778)
- [RGB LED Matrix Options](https://www.adafruit.com/category/327)
- [Power Supply Guide](https://learn.adafruit.com/rgb-led-matrices/powering)

### Community
- [CircuitPython Discord](https://discord.gg/circuitpython)
- [Adafruit Forums](https://forums.adafruit.com/)
- [Project Issues](https://github.com/yourusername/matrixportal-s3-dashboard/issues)

---

**Made with ❤️ for the maker community**
