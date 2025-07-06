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
                # adafruit_httpserver poll() method processes incoming requests
                # Some versions might return different types, so handle gracefully
                result = self.server.poll()
                # Poll might return a result we don't need to process
                if result is not None:
                    # Some implementations might return status info
                    pass
            except TypeError as e:
                # Handle specific type errors that might occur with polling
                print(f"Server poll type error (possibly harmless): {e}")
            except Exception as e:
                # More detailed error logging for other exceptions
                print(f"Server poll error: {e}")
                print(f"Error type: {type(e)}")
                # Don't print full traceback in production to avoid spam
                # import traceback
                # traceback.print_exception(type(e), e, e.__traceback__)
    
    def _create_json_response(self, request, data, status_code=200):
        """Create a JSON response with proper status code"""
        response = httpserver.JSONResponse(request, data)
        if status_code != 200:
            if status_code == 400:
                response.status = "400 Bad Request"
            elif status_code == 500:
                response.status = "500 Internal Server Error"
            else:
                response.status = f"{status_code} Error"
        print(f"_create_json_response: status={response.status}, data={data}")
        return response
    
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
        
        @self.server.route("/api/config", methods=["GET"])
        def handle_config_get(request):
            """Get current configuration"""
            return self._get_config_response(request)
        
        @self.server.route("/api/config", methods=["POST"])
        def handle_config_post(request):
            """Update configuration"""
            return self._update_config_response(request)
    
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
        .config-form {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            display: none;
        }
        .config-form h2 {
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #007cba;
            padding-bottom: 10px;
        }
        .form-section {
            margin: 20px 0;
            padding: 15px;
            background: white;
            border-radius: 6px;
            border: 1px solid #dee2e6;
        }
        .form-section h3 {
            margin: 0 0 15px 0;
            color: #495057;
            font-size: 1.1em;
        }
        .form-group {
            margin: 15px 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .form-group label {
            font-weight: 500;
            color: #495057;
            flex: 1;
        }
        .form-group input {
            flex: 1;
            max-width: 200px;
            padding: 8px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-size: 14px;
        }
        .form-group input[type="checkbox"] {
            max-width: 20px;
            margin-left: 10px;
        }
        .form-group input[type="range"] {
            max-width: 150px;
        }
        .form-actions {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
        }
        .form-actions button {
            min-width: 150px;
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
            <button onclick="toggleConfigForm()">⚙️ Configure</button>
        </div>
        
        <div id="jsonViewer" class="json-viewer"></div>
        
        <div id="configForm" class="config-form">
            <h2>⚙️ Configuration</h2>
            <form id="configFormData">
                <div class="form-section">
                    <h3>System Settings</h3>
                    <div class="form-group">
                        <label for="rotation_interval">Plugin Rotation Interval (seconds):</label>
                        <input type="number" id="rotation_interval" min="1" max="300" value="5">
                    </div>
                    <div class="form-group">
                        <label for="timezone">Timezone:</label>
                        <input type="text" id="timezone" value="UTC" placeholder="UTC">
                    </div>
                </div>
                
                <div class="form-section">
                    <h3>Display Settings</h3>
                    <div class="form-group">
                        <label for="display_brightness">Brightness:</label>
                        <input type="range" id="display_brightness" min="0" max="100" value="50">
                        <span id="brightness_value">50</span>%
                    </div>
                    <div class="form-group">
                        <label for="auto_brightness">Auto Brightness:</label>
                        <input type="checkbox" id="auto_brightness">
                    </div>
                </div>
                
                <div class="form-section">
                    <h3>Clock Plugin</h3>
                    <div class="form-group">
                        <label for="clock_enabled">Enabled:</label>
                        <input type="checkbox" id="clock_enabled" checked>
                    </div>
                    <div class="form-group">
                        <label for="clock_24h">24-hour Format:</label>
                        <input type="checkbox" id="clock_24h" checked>
                    </div>
                    <div class="form-group">
                        <label for="clock_seconds">Show Seconds:</label>
                        <input type="checkbox" id="clock_seconds">
                    </div>
                </div>
                
                <div class="form-actions">
                    <button type="button" onclick="saveConfig()">💾 Save Configuration</button>
                    <button type="button" onclick="loadConfig()">📥 Load Current Config</button>
                    <button type="button" onclick="toggleConfigForm()">❌ Cancel</button>
                </div>
            </form>
        </div>
        
        <div class="footer">
            <strong>💾 Memory:</strong> """ + str(gc.mem_free()) + """ bytes free<br>
            <strong>🔧 Configuration:</strong> Edit config.json and settings.toml to customize<br>
            <strong>📝 Logs:</strong> Check serial console for detailed information<br>
            <strong>💡 Tip:</strong> If config saves fail, disconnect USB and restart device
        </div>
    </div>
    
    <script>
        let statusData = null;
        let configData = null;
        
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
        
        function toggleConfigForm() {
            const form = document.getElementById('configForm');
            if (form.style.display === 'none' || !form.style.display) {
                form.style.display = 'block';
                loadConfig(); // Load current config when opening form
            } else {
                form.style.display = 'none';
            }
        }
        
        async function loadConfig() {
            try {
                const response = await fetch('/api/config');
                configData = await response.json();
                
                // Populate form fields
                document.getElementById('rotation_interval').value = configData.system?.rotation_interval || 5;
                document.getElementById('timezone').value = configData.system?.timezone || 'UTC';
                document.getElementById('display_brightness').value = configData.system?.display_brightness || 50;
                document.getElementById('brightness_value').textContent = configData.system?.display_brightness || 50;
                document.getElementById('auto_brightness').checked = configData.display?.brightness?.auto || false;
                document.getElementById('clock_enabled').checked = configData.plugins?.clock?.enabled !== false;
                document.getElementById('clock_24h').checked = configData.plugins?.clock?.format_24h !== false;
                document.getElementById('clock_seconds').checked = configData.plugins?.clock?.display_seconds || false;
                
                console.log('Configuration loaded:', configData);
            } catch (error) {
                alert('Error loading configuration: ' + error.message);
            }
        }
        
        async function saveConfig() {
            try {
                // Build configuration object from form
                const newConfig = {
                    system: {
                        wifi_ssid: configData?.system?.wifi_ssid || "",
                        wifi_password: configData?.system?.wifi_password || "",
                        display_brightness: parseInt(document.getElementById('display_brightness').value),
                        rotation_interval: parseInt(document.getElementById('rotation_interval').value),
                        timezone: document.getElementById('timezone').value
                    },
                    display: {
                        width: 64,
                        height: 64,
                        bit_depth: 6,
                        brightness: {
                            auto: document.getElementById('auto_brightness').checked,
                            manual: parseInt(document.getElementById('display_brightness').value) / 100,
                            day: 0.8,
                            night: 0.2
                        }
                    },
                    network: configData?.network || {
                        timeout: 10,
                        retry_count: 3,
                        retry_delay: 5
                    },
                    web: {
                        port: 80,
                        enabled: true
                    },
                    plugins: {
                        clock: {
                            enabled: document.getElementById('clock_enabled').checked,
                            display_seconds: document.getElementById('clock_seconds').checked,
                            format_24h: document.getElementById('clock_24h').checked
                        }
                    }
                };
                
                // Send POST request
                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(newConfig)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    alert('Configuration saved successfully!');
                    toggleConfigForm(); // Close form
                } else {
                    if (result.errno === 30) {
                        alert('Cannot save configuration: Filesystem is read-only.\\n\\nTo fix this:\\n1. Disconnect USB cable from computer\\n2. Restart the MatrixPortal S3 device\\n3. Connect to WiFi and try again');
                    } else {
                        alert('Error saving configuration: ' + (result.error || 'Unknown error'));
                    }
                }
            } catch (error) {
                alert('Error saving configuration: ' + error.message);
            }
        }
        
        // Update brightness display
        document.addEventListener('DOMContentLoaded', function() {
            const brightnessSlider = document.getElementById('display_brightness');
            const brightnessValue = document.getElementById('brightness_value');
            
            brightnessSlider.addEventListener('input', function() {
                brightnessValue.textContent = this.value;
            });
        });
        
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
    
    def _update_config_response(self, request):
        """Update configuration data"""
        print("POST /api/config received")
        
        # Initialize all variables at the start to avoid scope issues
        config_data = None
        body = None
        body_str = None
        
        try:
            if not self.config_manager:
                print("Config manager not available")
                return self._create_json_response(request, {"error": "Config manager not available"}, 500)
            
            # Get the request body
            try:
                body = request.body
                print(f"Got body via request.body: {type(body)}")
            except Exception as e:
                print(f"Error accessing request body: {e}")
                return self._create_json_response(request, {"error": f"Error accessing request body: {str(e)}"}, 400)
            
            if not body:
                print("No body data provided")
                return self._create_json_response(request, {"error": "No data provided"}, 400)
            
            # Parse JSON data
            print(f"Parsing body of type: {type(body)}")
            
            try:
                if isinstance(body, (bytes, bytearray)):
                    body_str = body.decode('utf-8')
                    print(f"Decoded body: {body_str[:100]}...")
                    config_data = json.loads(body_str)
                    print("Successfully parsed JSON from bytes")
                elif isinstance(body, str):
                    config_data = json.loads(body)
                    print("Successfully parsed JSON from string")
                else:
                    config_data = body
                    print(f"Body already parsed as: {type(body)}")
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Parsing error: {e}")
                return self._create_json_response(request, {"error": f"Invalid JSON: {str(e)}"}, 400)
            
            # Validate configuration
            print(f"Validating config structure, type: {type(config_data)}")
            if not isinstance(config_data, dict):
                print("Config is not a dictionary")
                return self._create_json_response(request, {"error": "Configuration must be a JSON object"}, 400)
            
            print("Running config validation")
            if not self.config_manager.validate_config(config_data):
                print("Config validation failed")
                return self._create_json_response(request, {"error": "Configuration validation failed"}, 400)
            
            # Save configuration
            print("Config validation passed, attempting to save")
            try:
                success = self.config_manager.save_config(config_data)
                if success:
                    print("Config saved successfully")
                    return httpserver.JSONResponse(request, {"success": True, "message": "Configuration updated successfully"})
                else:
                    print("Config save returned False")
                    return self._create_json_response(request, {"error": "Failed to save configuration"}, 500)
            except OSError as os_error:
                print(f"OSError during config save: {os_error}, errno: {os_error.errno}")
                if os_error.errno == 30:  # Read-only filesystem
                    return self._create_json_response(request, {
                        "error": "Read-only filesystem. Disconnect USB cable and restart device to make filesystem writable.",
                        "errno": 30
                    }, 500)
                else:
                    return self._create_json_response(request, {"error": f"Filesystem error: {str(os_error)}"}, 500)
                
        except Exception as e:
            print(f"Unexpected error in _update_config_response: {e}")
            import traceback
            traceback.print_exception(type(e), e, e.__traceback__)
            return self._create_json_response(request, {"error": str(e)}, 500)
    
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
