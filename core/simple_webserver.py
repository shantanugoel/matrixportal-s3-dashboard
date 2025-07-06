"""
Simple web server for MatrixPortal S3 Dashboard configuration
Lightweight HTTP server for basic configuration interface
"""
import asyncio
import json
import gc
import wifi
import socketpool

class SimpleWebServer:
    """Simplified web server for dashboard configuration"""
    
    def __init__(self, port=80, config_manager=None, plugin_manager=None, scheduler=None):
        self.port = port
        self.config_manager = config_manager
        self.plugin_manager = plugin_manager
        self.scheduler = scheduler
        
        # Server state
        self.running = False
        self.socket_pool = None
        
    async def start(self):
        """Start the web server"""
        if self.running:
            return
        
        if not wifi.radio.connected:
            print("WiFi not connected, cannot start web server")
            return False
        
        self.running = True
        print(f"Simple web server starting on port {self.port}")
        print(f"Access at: http://{wifi.radio.ipv4_address}:{self.port}")
        
        # Start server task
        asyncio.create_task(self._server_task())
        return True
    
    async def stop(self):
        """Stop the web server"""
        self.running = False
        print("Simple web server stopped")
    
    async def _server_task(self):
        """Main server task - simplified approach"""
        self.socket_pool = socketpool.SocketPool(wifi.radio)
        
        while self.running:
            try:
                # Create a new socket for each request (simpler approach)
                server_socket = self.socket_pool.socket(
                    self.socket_pool.AF_INET, 
                    self.socket_pool.SOCK_STREAM
                )
                
                try:
                    server_socket.setsockopt(
                        self.socket_pool.SOL_SOCKET, 
                        self.socket_pool.SO_REUSEADDR, 
                        1
                    )
                    server_socket.bind(('', self.port))
                    server_socket.listen(1)
                    server_socket.settimeout(1)  # 1 second timeout
                    
                    # Accept one connection
                    try:
                        client_socket, addr = server_socket.accept()
                        await self._handle_client(client_socket, addr)
                    except OSError:
                        # Timeout or no connection - continue loop
                        pass
                        
                finally:
                    server_socket.close()
                    
                # Brief yield to other tasks
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Server task error: {e}")
                await asyncio.sleep(1)
    
    async def _handle_client(self, client_socket, addr):
        """Handle client request"""
        try:
            # Read request
            request_data = b""
            client_socket.settimeout(2)  # 2 second timeout for reading
            
            try:
                while True:
                    chunk = client_socket.recv(1024)
                    if not chunk:
                        break
                    request_data += chunk
                    if b"\r\n\r\n" in request_data:
                        break
            except OSError:
                pass  # Timeout
            
            if request_data:
                request = request_data.decode('utf-8', errors='ignore')
                response = self._handle_request(request)
                
                # Send response
                client_socket.send(response.encode('utf-8'))
            
        except Exception as e:
            print(f"Client handling error: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
            gc.collect()
    
    def _handle_request(self, request):
        """Handle HTTP request"""
        try:
            lines = request.split('\r\n')
            if not lines:
                return self._error_response(400, "Bad Request")
            
            request_line = lines[0].split(' ')
            if len(request_line) < 2:
                return self._error_response(400, "Bad Request")
            
            method = request_line[0]
            path = request_line[1]
            
            # Route request
            if method == "GET":
                return self._handle_get(path)
            elif method == "POST":
                return self._handle_post(path, request)
            else:
                return self._error_response(405, "Method Not Allowed")
                
        except Exception as e:
            print(f"Request handling error: {e}")
            return self._error_response(500, "Internal Server Error")
    
    def _handle_get(self, path):
        """Handle GET requests"""
        if path == "/" or path == "/index.html":
            return self._serve_index()
        elif path == "/api/config":
            return self._get_config()
        elif path == "/api/status":
            return self._get_status()
        elif path == "/api/plugins":
            return self._get_plugins()
        else:
            return self._error_response(404, "Not Found")
    
    def _handle_post(self, path, request):
        """Handle POST requests"""
        if path == "/api/config":
            return self._update_config(request)
        else:
            return self._error_response(404, "Not Found")
    
    def _serve_index(self):
        """Serve simple configuration page"""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Config</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        .section { margin: 15px 0; padding: 15px; border: 1px solid #ddd; border-radius: 4px; }
        button { padding: 10px 15px; margin: 5px; background: #007cba; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #005a87; }
        input, select { padding: 8px; margin: 5px; border: 1px solid #ddd; border-radius: 4px; }
        .status { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .status.ok { background-color: #d4edda; color: #155724; }
        .status.error { background-color: #f8d7da; color: #721c24; }
        .info { background-color: #d1ecf1; color: #0c5460; padding: 10px; border-radius: 4px; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 MatrixPortal Dashboard</h1>
        
        <div class="info">
            Simple configuration interface for your dashboard
        </div>
        
        <div class="section">
            <h2>📊 System Status</h2>
            <div id="status">Loading...</div>
            <button onclick="refreshStatus()">🔄 Refresh</button>
        </div>
        
        <div class="section">
            <h2>⚙️ Settings</h2>
            <label>Display Rotation (seconds): <input type="number" id="rotationTime" value="5" min="1" max="60"></label><br><br>
            <label>Brightness: <input type="range" id="brightness" min="0" max="100" value="50"> <span id="brightnessValue">50</span>%</label><br><br>
            <button onclick="updateSettings()">💾 Save Settings</button>
        </div>
        
        <div class="section">
            <h2>🔌 Plugins</h2>
            <div id="plugins">Loading...</div>
            <button onclick="loadPlugins()">🔄 Refresh Plugins</button>
        </div>
    </div>

    <script>
        // Update brightness display
        document.getElementById('brightness').oninput = function() {
            document.getElementById('brightnessValue').textContent = this.value;
        }

        async function refreshStatus() {
            try {
                const response = await fetch('/api/status');
                const status = await response.json();
                document.getElementById('status').innerHTML = 
                    `<div class="status ok">
                        <strong>System:</strong> ${status.running ? 'Running ✅' : 'Stopped ❌'}<br>
                        <strong>Network:</strong> ${status.network ? status.network.connected ? 'Connected ✅' : 'Disconnected ❌' : 'Unknown'}<br>
                        <strong>IP:</strong> ${status.network ? status.network.ip_address || 'N/A' : 'N/A'}<br>
                        <strong>Plugins:</strong> ${status.plugins || 0}<br>
                        <strong>Memory:</strong> ${status.memory || 'Unknown'} bytes free
                    </div>`;
            } catch (error) {
                document.getElementById('status').innerHTML = 
                    `<div class="status error">❌ Error loading status: ${error.message}</div>`;
            }
        }

        async function loadPlugins() {
            try {
                const response = await fetch('/api/plugins');
                const plugins = await response.json();
                let html = '';
                
                if (Object.keys(plugins).length === 0) {
                    html = '<p>No plugins found</p>';
                } else {
                    for (const [name, plugin] of Object.entries(plugins)) {
                        html += `<div style="margin: 10px 0; padding: 10px; border: 1px solid #eee; border-radius: 4px;">
                            <strong>📦 ${plugin.name || name}</strong> v${plugin.version || '1.0'}<br>
                            <em>${plugin.description || 'No description'}</em><br>
                            <small>Status: ${plugin.enabled ? '✅ Enabled' : '❌ Disabled'}</small>
                        </div>`;
                    }
                }
                
                document.getElementById('plugins').innerHTML = html;
            } catch (error) {
                document.getElementById('plugins').innerHTML = '❌ Error loading plugins';
            }
        }

        async function updateSettings() {
            const rotationTime = document.getElementById('rotationTime').value;
            const brightness = document.getElementById('brightness').value;
            
            try {
                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        display: {
                            rotation_time: parseInt(rotationTime),
                            brightness: parseInt(brightness)
                        }
                    })
                });
                
                if (response.ok) {
                    alert('✅ Settings updated successfully!');
                } else {
                    alert('❌ Error updating settings');
                }
            } catch (error) {
                alert('❌ Error: ' + error.message);
            }
        }

        // Load initial data
        refreshStatus();
        loadPlugins();
        
        // Auto-refresh status every 30 seconds
        setInterval(refreshStatus, 30000);
    </script>
</body>
</html>"""
        return self._http_response("text/html", html)
    
    def _get_config(self):
        """Get current configuration"""
        try:
            if self.config_manager:
                config = self.config_manager.load_config()
            else:
                config = {"error": "No config manager"}
            
            response = json.dumps(config)
            return self._http_response("application/json", response)
        except Exception as e:
            return self._error_response(500, f"Config error: {e}")
    
    def _get_status(self):
        """Get system status"""
        try:
            status = {
                'running': True,
                'network': {
                    'connected': wifi.radio.connected,
                    'ip_address': str(wifi.radio.ipv4_address) if wifi.radio.connected else None,
                    'signal_strength': wifi.radio.rssi if wifi.radio.connected else None
                },
                'plugins': len(self.plugin_manager.plugins) if self.plugin_manager else 0,
                'memory': gc.mem_free(),
                'scheduler': self.scheduler.get_status() if self.scheduler else {}
            }
            
            response = json.dumps(status)
            return self._http_response("application/json", response)
        except Exception as e:
            return self._error_response(500, f"Status error: {e}")
    
    def _get_plugins(self):
        """Get plugin information"""
        try:
            plugins = {}
            if self.plugin_manager:
                for name, metadata in self.plugin_manager.list_plugins().items():
                    plugins[name] = {
                        'name': metadata.name,
                        'version': metadata.version,
                        'description': metadata.description,
                        'enabled': True  # TODO: Get actual enabled state from config
                    }
            
            response = json.dumps(plugins)
            return self._http_response("application/json", response)
        except Exception as e:
            return self._error_response(500, f"Plugin error: {e}")
    
    def _update_config(self, request):
        """Update configuration"""
        try:
            # Extract JSON body
            body_start = request.find('\r\n\r\n')
            if body_start == -1:
                return self._error_response(400, "No request body")
            
            body = request[body_start + 4:]
            config_update = json.loads(body)
            
            # TODO: Actually update configuration
            print(f"Config update received: {config_update}")
            
            response = json.dumps({'success': True, 'message': 'Configuration updated'})
            return self._http_response("application/json", response)
            
        except Exception as e:
            return self._error_response(500, f"Update error: {e}")
    
    def _http_response(self, content_type, body):
        """Generate HTTP response"""
        body_bytes = body.encode('utf-8') if isinstance(body, str) else body
        return f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(body_bytes)}\r\nConnection: close\r\n\r\n{body}"
    
    def _error_response(self, code, message):
        """Generate HTTP error response"""
        return f"HTTP/1.1 {code} {message}\r\nContent-Type: text/plain\r\nContent-Length: {len(message)}\r\nConnection: close\r\n\r\n{message}"
