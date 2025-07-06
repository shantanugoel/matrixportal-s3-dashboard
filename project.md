# MatrixPortal S3 Dashboard Project

## Project Overview

A modular dashboard system for Adafruit MatrixPortal S3 with 64x64 RGB LED matrix, built in CircuitPython. The system displays rotating content including health stats, sports scores, F1 racing data, and screensaver GIFs through a plugin-based architecture.

## Architecture

### System Components

```
┌─────────────┐   ① register()   ┌───────────────┐
│  Plugin A   │◄───────────────┐ │   Plugin B    │
│ (Cricket)   │                │ │ (Health)      │
└─────────────┘                │ └───────────────┘
        ▲                      │         ▲
        │ pull()/push_cb()     │         │
        └──────┐         ┌─────┘         └─────┐
               ▼         ▼                    ▼
             ┌───────────────────────────────────┐
             │        Plugin Manager             │
             └───────────────────────────────────┘
                         ▲      ▲
          metadata & cfg │      │ render()→Frame
                         │      ▼
             ┌───────────────────────────────────┐
             │      Core Scheduler (asyncio)     │
             └───────────────────────────────────┘
                             │ next Frame
                             ▼
             ┌───────────────────────────────────┐
             │       Display Engine (RGB)        │
             └───────────────────────────────────┘

             ┌───────────────────────────────────┐
Wi-Fi Core → │  Network Task (socket, MQTT, HTTP)│
             └───────────────────────────────────┘
                      ▲             ▲
                      │             │ REST/WS
                      │             │
             ┌───────────────────────────────────┐
             │    Web Config Server (TinyAPI)    │
             └───────────────────────────────────┘
                      ▲
                      │ JSON in /config.json
                      ▼
             ┌───────────────────────────────────┐
             │  Persistence (Flash + PSRAM)      │
             └───────────────────────────────────┘
```

### Core Modules

#### 1. Plugin Manager
- **Location**: `/plugins/` directory
- **Interface**: Each plugin folder contains `__init__.py` with:
  - `metadata`: dict(name, version, default_config, refresh_type["push"|"pull"], interval)
  - `async init(cfg)`: optional startup
  - `async pull()`: for polling data
  - `push_cb(topic,payload)`: for MQTT/webhook pushes
  - `render(state, frame)`: draw onto shared FrameBuffer (64×64)

#### 2. Core Scheduler (asyncio)
- Manages periodic tasks per plugin interval
- Rotator coroutine drives "current scene" time slice (~5s)
- Cancels/creates tasks when plugins enabled/disabled
- Uses watchdog.wdt_feed() in main loop

#### 3. Display Engine
- Uses `adafruit_matrixportal.MatrixPortal` + `displayio`
- Pre-allocates two `displayio.Bitmap` layers (double buffer) in PSRAM
- Helpers for text, sprites, scrolling ticker
- GIF support: palette-compressed 64×64, stream one frame at a time

#### 4. Network Layer
- HTTP GET/POST via `adafruit_requests`
- MQTT via `MiniMQTT` (keep_alive = 120, auto-reconnect)
- Shared socket pool
- Exponential-backoff reconnect

#### 5. Web Configuration Server
- Tiny HTTP server (socket + select)
- Serves static `/www/index.html` + JSON REST endpoints
- Endpoints: GET/POST `/api/config`, GET `/api/plugins`
- Phone/PC browser interface

#### 6. Persistence Layer
- `/config.json` ≤4KB with atomic writes
- `/data/` cache files on SD card
- CRC corruption detection

## Project Structure

```
/
├── boot.py              # PSRAM enable, safe mode, Wi-Fi init
├── main.py              # mount SD, start Core
├── core/
│   ├── __init__.py
│   ├── scheduler.py     # asyncio scheduler
│   ├── display.py       # display engine
│   ├── network.py       # network layer
│   ├── config.py        # configuration management
│   └── webserver.py     # web configuration server
├── plugins/
│   ├── clock/           # example plugin
│   ├── cricket/         # cricket scores
│   ├── health/          # Apple Health data
│   ├── f1/              # F1 racing data
│   └── screensaver/     # GIF screensaver
├── www/
│   ├── index.html       # configuration UI
│   ├── style.css
│   └── app.js
├── data/                # cached data, sprites
└── config.json          # system configuration
```

## Phase-wise Implementation Plan

### Phase 1: Core Infrastructure (High Priority)
1. **Project Setup**
   - Create directory structure
   - Set up boot.py with PSRAM initialization
   - Basic main.py with error handling

2. **Plugin Interface**
   - Define plugin base class/interface
   - Create plugin discovery mechanism
   - Implement plugin registration system

3. **Core Scheduler**
   - Implement asyncio-based scheduler
   - Add plugin rotation logic
   - Basic timing and task management

4. **Display Engine**
   - Set up displayio with double buffering
   - PSRAM allocation for frame buffers
   - Basic text rendering helpers

### Phase 2: Configuration & Networking (Medium Priority)
1. **Web Configuration Server**
   - Implement tiny HTTP server
   - Create REST API endpoints
   - Basic HTML/JS configuration interface

2. **Persistence Layer**
   - JSON configuration management
   - Atomic write operations
   - Configuration validation

3. **Network Reliability**
   - Watchdog implementation
   - Wi-Fi reconnection logic
   - Captive portal fallback

4. **Example Plugin**
   - Create Clock plugin as template
   - Test plugin interface
   - Validate architecture

### Phase 3: Feature Plugins (Low Priority)
1. **Cricket Scores Plugin**
   - Pull-based data fetching
   - API integration
   - Score display formatting

2. **Apple Health Plugin**
   - MQTT push-based data
   - Steps comparison display
   - Health metrics visualization

3. **F1 Racing Plugin**
   - Real-time race data
   - Position and timing display
   - Race status indicators

4. **Screensaver Plugin**
   - GIF frame streaming
   - Memory-optimized playback
   - Internet GIF fetching

## Technical Specifications

### Hardware Requirements
- Adafruit MatrixPortal S3
- 64x64 P3 RGB LED matrix (Waveshare)
- SD card (optional, for data caching)
- Wi-Fi network access

### Software Requirements
- CircuitPython ≥ 9.x
- Required libraries:
  - `adafruit_matrixportal`
  - `adafruit_requests`
  - `adafruit_minimqtt`
  - `displayio`
  - `asyncio`

### Performance Considerations
- **Memory Management**: Pre-allocate buffers, use PSRAM for large objects
- **Network Efficiency**: Async operations, connection pooling
- **Display Refresh**: Double buffering, manual refresh control
- **CPU Usage**: Keep awaitable sections <10ms for smooth scrolling

### Plugin Development Guidelines
- Each plugin in separate folder under `/plugins/`
- Implement standard interface methods
- Use async/await for network operations
- Minimize memory allocations in render loop
- Include metadata with configuration schema

## Configuration Schema

```json
{
  "system": {
    "wifi_ssid": "your_wifi",
    "wifi_password": "your_password",
    "display_brightness": 50,
    "rotation_interval": 5,
    "timezone": "UTC"
  },
  "plugins": {
    "clock": {
      "enabled": true,
      "display_seconds": true,
      "format_24h": true
    },
    "cricket": {
      "enabled": false,
      "api_key": "your_api_key",
      "refresh_interval": 30
    },
    "health": {
      "enabled": false,
      "mqtt_broker": "broker.example.com",
      "mqtt_topic": "health/steps"
    }
  }
}
```

## Development Workflow

1. **Desktop Development**
   - Unit test plugins on CPython with stub displayio
   - CI/CD with GitHub Actions
   - Code formatting and linting

2. **Deployment**
   - Bundle www/ assets to .mpy files
   - Copy to /Volumes/CIRCUITPY
   - Auto-reload and testing

3. **Debugging**
   - Serial console monitoring
   - Memory usage tracking
   - Network connectivity debugging

## Success Metrics

- **Performance**: Smooth 60fps display refresh
- **Reliability**: 48+ hour continuous operation
- **Memory**: <80% RAM usage under normal load
- **Extensibility**: Add new plugin in <1 hour
- **Usability**: Configuration changes via web UI in <2 minutes

## Future Enhancements

- OTA updates via WebDAV
- BLE configuration for initial setup
- Plugin marketplace/repository
- Real-time collaboration features
- Voice control integration
- Mobile app companion

---

*Last Updated: Project Planning Phase*
*Next Milestone: Phase 1 - Core Infrastructure*
