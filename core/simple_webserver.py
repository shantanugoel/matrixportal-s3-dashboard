"""
Proper web server for MatrixPortal S3 Dashboard using adafruit_httpserver
Uses the official CircuitPython HTTP server library
"""
import wifi
import socketpool
import gc
import json

try:
    import adafruit_httpserver as httpserver
    HTTPSERVER_AVAILABLE = True
except ImportError:
    print("adafruit_httpserver not available, using fallback")
    HTTPSERVER_AVAILABLE = False

class SimpleWebServer:
    """Web server using adafruit_httpserver library"""
    
    def __init__(self, port=80, config_manager=None, plugin_manager=None, scheduler=None):
        self.port = port
        self.config_manager = config_manager
        self.plugin_manager = plugin_manager
        self.scheduler = scheduler
        self.running = False
        self.server = None
        
    async def start(self):
        """Start the web server"""
        if self.running:
            return
        
        if not wifi.radio.connected:
            print("WiFi not connected, cannot start web server")
            return False
        
        if not HTTPSERVER_AVAILABLE:
            print("adafruit_httpserver library not available")
            return False
        
        try:
            # Create socket pool
            pool = socketpool.SocketPool(wifi.radio)
            
            # Create server instance
            self.server = httpserver.Server(pool, "/static")
            
            # Register routes
            self._register_routes()
            
            # Start the server
            self.server.start(host="0.0.0.0", port=self.port)
            
            self.running = True
            print(f"HTTP server started on port {self.port}")
            print(f"Access at: http://{wifi.radio.ipv4_address}:{self.port}")
            
            return True
            
        except Exception as e:
            print(f"Failed to start web server: {e}")
            return False
    
    async def stop(self):
        """Stop the web server"""
        if self.server and self.running:
            try:
                self.server.stop()
            except:
                pass
        self.running = False
        print("Web server stopped")
    
    def poll(self):
        """Poll for incoming requests - call this regularly"""
        if self.server and self.running:
            try:
                self.server.poll()
            except Exception as e:
                print(f"Server poll error: {e}")
    
    def _register_routes(self):
        """Register HTTP routes"""
        
        @self.server.route("/")
        def handle_root(request):
            """Serve the main dashboard page"""
            return self._create_html_response(request)
        
        @self.server.route("/api/status")
        def handle_status(request):
            """Serve JSON status information"""
            return self._create_status_response(request)
        
        @self.server.route("/api/config")
        def handle_config_get(request):
            """Get current configuration"""
            return self._get_config_response(request)
    
    def _create_html_response(self, request):
        """Create the main HTML dashboard page"""
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MatrixPortal S3 Dashboard</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; 
            padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container { 
            max-width: 600px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 12px; 
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        h1 { 
            color: #333; 
            text-align: center; 
            margin-bottom: 30px;
            font-size: 2.2em;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .status-card { 
            background: linear-gradient(135deg, #e8f5e8 0%, #f0f8f0 100%);
            border: 2px solid #c3e6c3; 
            padding: 20px; 
            border-radius: 8px;
            transition: transform 0.2s ease;
        }
        .status-card:hover {
            transform: translateY(-2px);
        }
        .status-card h3 {
            margin: 0 0 15px 0;
            color: #2d5a2d;
            font-size: 1.3em;
        }
        .info-row { 
            margin: 10px 0; 
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .label { 
            font-weight: 600; 
            color: #555; 
        }
        .value { 
            color: #333;
            font-family: 'Monaco', 'Menlo', monospace;
            background: #f8f9fa;
            padding: 2px 6px;
            border-radius: 4px;
        }
        .button-group {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin: 30px 0;
            flex-wrap: wrap;
        }
        button { 
            background: linear-gradient(135deg, #007cba 0%, #0056b3 100%);
            color: white; 
            border: none; 
            padding: 12px 20px; 
            border-radius: 6px; 
            cursor: pointer; 
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s ease;
            min-width: 120px;
        }
        button:hover { 
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,124,186,0.3);
        }
        button:active {
            transform: translateY(0);
        }
        .footer {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            font-size: 14px;
            color: #666;
            border-left: 4px solid #007cba;
        }
        .status-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #28a745;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        .json-viewer {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 15px;
            margin: 10px 0;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 12px;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 MatrixPortal S3 Dashboard</h1>
        
        <div class="status-grid">
            <div class="status-card">
                <h3><span class="status-indicator"></span>System Status</h3>
                <div class="info-row">
                    <span class="label">Status:</span> 
                    <span class="value">Online</span>
                </div>
                <div class="info-row">
                    <span class="label">Display:</span> 
                    <span class="value">64×64 LED Matrix</span>
                </div>
                <div class="info-row">
                    <span class="label">Current Plugin:</span> 
                    <span class="value">Digital Clock</span>
                </div>
            </div>
            
            <div class="status-card">
                <h3>📶 Network Info</h3>
                <div class="info-row">
                    <span class="label">WiFi:</span> 
                    <span class="value">Connected</span>
                </div>
                <div class="info-row">
                    <span class="label">IP Address:</span> 
                    <span class="value">""" + str(wifi.radio.ipv4_address) + """</span>
                </div>
                <div class="info-row">
                    <span class="label">Signal:</span> 
                    <span class="value">""" + self._get_signal_strength() + """</span>
                </div>
            </div>
        </div>
        
        <div class="button-group">
            <button onclick="window.location.reload()">🔄 Refresh</button>
            <button onclick="getStatus()">📊 Get Status</button>
            <button onclick="toggleJsonViewer()">🔍 View JSON</button>
        </div>
        
        <div id="jsonViewer" class="json-viewer"></div>
        
        <div class="footer">
            <strong>💾 Memory:</strong> """ + str(gc.mem_free()) + """ bytes free<br>
            <strong>🔧 Configuration:</strong> Edit config.json and settings.toml to customize<br>
            <strong>📝 Logs:</strong> Check serial console for detailed information
        </div>
    </div>
    
    <script>
        let statusData = null;
        
        async function getStatus() {
            try {
                const response = await fetch('/api/status');
                statusData = await response.json();
                alert('Status loaded! Click "View JSON" to see details.');
            } catch (error) {
                alert('Error loading status: ' + error.message);
            }
        }
        
        function toggleJsonViewer() {
            const viewer = document.getElementById('jsonViewer');
            if (viewer.style.display === 'none' || !viewer.style.display) {
                if (statusData) {
                    viewer.textContent = JSON.stringify(statusData, null, 2);
                    viewer.style.display = 'block';
                } else {
                    alert('Click "Get Status" first to load data.');
                }
            } else {
                viewer.style.display = 'none';
            }
        }
        
        // Auto-refresh page every 60 seconds
        setTimeout(() => window.location.reload(), 60000);
    </script>
</body>
</html>"""
        
        return httpserver.Response(request, html_content, content_type="text/html")
    
    def _create_status_response(self, request):
        """Create JSON status response"""
        try:
            status_data = {
                "system": {
                    "running": True,
                    "memory_free": gc.mem_free(),
                    "plugins_loaded": len(self.plugin_manager.plugins) if self.plugin_manager else 0
                },
                "network": {
                    "connected": wifi.radio.connected,
                    "ip_address": str(wifi.radio.ipv4_address),
                    "signal_strength": self._get_signal_strength_raw(),
                    "mac_address": self._get_mac_address()
                },
                "display": {
                    "width": 64,
                    "height": 64,
                    "active": True
                },
                "scheduler": self.scheduler.get_status() if self.scheduler else {}
            }
            
            return httpserver.JSONResponse(request, status_data)
            
        except Exception as e:
            error_data = {"error": str(e)}
            return httpserver.JSONResponse(request, error_data, status=500)
    
    def _get_config_response(self, request):
        """Get configuration data"""
        try:
            if self.config_manager:
                config = self.config_manager.load_config()
                return httpserver.JSONResponse(request, config)
            else:
                return httpserver.JSONResponse(request, {"error": "Config manager not available"}, status=500)
        except Exception as e:
            return httpserver.JSONResponse(request, {"error": str(e)}, status=500)
    
    def _get_signal_strength(self):
        """Get WiFi signal strength as formatted string"""
        try:
            rssi = wifi.radio.rssi
            return f"{rssi} dBm"
        except AttributeError:
            return "Unknown"
    
    def _get_signal_strength_raw(self):
        """Get WiFi signal strength as raw value"""
        try:
            return wifi.radio.rssi
        except AttributeError:
            return None
    
    def _get_mac_address(self):
        """Get MAC address safely"""
        try:
            mac = wifi.radio.mac_address
            if isinstance(mac, (bytes, bytearray)):
                return ':'.join(['{:02x}'.format(b) for b in mac])
            else:
                return str(mac)
        except AttributeError:
            return "Unknown"

# Fallback simple server for when adafruit_httpserver is not available
class FallbackWebServer:
    """Fallback web server when adafruit_httpserver is not available"""
    
    def __init__(self, port=80, config_manager=None, plugin_manager=None, scheduler=None):
        print("Using fallback web server - install adafruit_httpserver for better functionality")
        
    async def start(self):
        print("Fallback web server: adafruit_httpserver library required")
        return False
    
    async def stop(self):
        pass
    
    def poll(self):
        pass

# Use the appropriate server based on library availability
if HTTPSERVER_AVAILABLE:
    WebServer = SimpleWebServer
else:
    WebServer = FallbackWebServer
