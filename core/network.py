"""
Network management for MatrixPortal S3 Dashboard
Handles Wi-Fi connection, reconnection, and network reliability
"""
import wifi
import socketpool
import ssl
import time
import asyncio

class NetworkManager:
    """Manages Wi-Fi connectivity and network operations"""
    
    def __init__(self, config):
        self.config = config
        self.ssid = config.get('ssid', '')
        self.password = config.get('password', '')
        self.timeout = config.get('timeout', 10)
        self.retry_count = config.get('retry_count', 3)
        self.retry_delay = config.get('retry_delay', 5)
        
        # Network state
        self.connected = False
        self.ip_address = None
        self.last_connection_attempt = 0
        self.connection_failures = 0
        
        # Socket pool for reuse
        self.socket_pool = None
        self.ssl_context = None
        
    async def connect(self):
        """Connect to Wi-Fi network"""
        if not self.ssid:
            print("No Wi-Fi SSID configured")
            return False
        
        print(f"Connecting to Wi-Fi network: {self.ssid}")
        
        for attempt in range(self.retry_count):
            try:
                # Disconnect if already connected
                if wifi.radio.connected:
                    wifi.radio.stop_station()
                
                # Connect to network
                wifi.radio.connect(self.ssid, self.password, timeout=self.timeout)
                
                # Wait for connection
                start_time = time.monotonic()
                while not wifi.radio.connected and (time.monotonic() - start_time) < self.timeout:
                    await asyncio.sleep(0.1)
                
                if wifi.radio.connected:
                    self.connected = True
                    self.ip_address = str(wifi.radio.ipv4_address)
                    self.connection_failures = 0
                    
                    # Initialize socket pool
                    self.socket_pool = socketpool.SocketPool(wifi.radio)
                    self.ssl_context = ssl.create_default_context()
                    
                    print(f"Connected to Wi-Fi: {self.ip_address}")
                    return True
                else:
                    raise Exception("Connection timeout")
                    
            except Exception as e:
                self.connection_failures += 1
                print(f"Wi-Fi connection attempt {attempt + 1} failed: {e}")
                
                if attempt < self.retry_count - 1:
                    await asyncio.sleep(self.retry_delay)
        
        self.connected = False
        self.last_connection_attempt = time.monotonic()
        print("Wi-Fi connection failed after all attempts")
        return False
    
    async def disconnect(self):
        """Disconnect from Wi-Fi network"""
        try:
            if wifi.radio.connected:
                wifi.radio.stop_station()
            
            self.connected = False
            self.ip_address = None
            self.socket_pool = None
            self.ssl_context = None
            
            print("Disconnected from Wi-Fi")
            
        except Exception as e:
            print(f"Error disconnecting: {e}")
    
    async def reconnect(self):
        """Attempt to reconnect to Wi-Fi"""
        # Don't attempt reconnection too frequently
        if time.monotonic() - self.last_connection_attempt < 30:
            return False
        
        print("Attempting Wi-Fi reconnection...")
        return await self.connect()
    
    def is_connected(self):
        """Check if connected to Wi-Fi"""
        try:
            # Check both our state and actual radio state
            if wifi.radio.connected and self.connected:
                return True
            else:
                self.connected = False
                return False
        except:
            self.connected = False
            return False
    
    def get_socket_pool(self):
        """Get socket pool for network operations"""
        return self.socket_pool
    
    def get_ssl_context(self):
        """Get SSL context for secure connections"""
        return self.ssl_context
    
    def get_ip_address(self):
        """Get current IP address"""
        return self.ip_address
    
    def get_mac_address(self):
        """Get MAC address"""
        try:
            mac = wifi.radio.mac_address
            return ':'.join(['{:02x}'.format(b) for b in mac])
        except:
            return "Unknown"
    
    def get_signal_strength(self):
        """Get Wi-Fi signal strength in dBm"""
        try:
            if wifi.radio.connected:
                return wifi.radio.rssi
            return -100
        except:
            return -100
    
    def get_network_info(self):
        """Get detailed network information"""
        return {
            'connected': self.is_connected(),
            'ssid': self.ssid,
            'ip_address': self.ip_address,
            'mac_address': self.get_mac_address(),
            'signal_strength': self.get_signal_strength(),
            'connection_failures': self.connection_failures,
            'last_attempt': self.last_connection_attempt
        }
    
    def scan_networks(self):
        """Scan for available Wi-Fi networks"""
        try:
            networks = []
            for network in wifi.radio.start_scanning_networks():
                networks.append({
                    'ssid': network.ssid,
                    'rssi': network.rssi,
                    'channel': network.channel,
                    'security': str(network.authmode)
                })
            
            wifi.radio.stop_scanning_networks()
            return networks
            
        except Exception as e:
            print(f"Network scan error: {e}")
            return []
    
    def update_credentials(self, ssid, password):
        """Update Wi-Fi credentials"""
        self.ssid = ssid
        self.password = password
        self.config['ssid'] = ssid
        self.config['password'] = password
        
        print(f"Updated Wi-Fi credentials for: {ssid}")
    
    def get_status(self):
        """Get network manager status"""
        return {
            'connected': self.is_connected(),
            'ip_address': self.ip_address,
            'signal_strength': self.get_signal_strength(),
            'connection_failures': self.connection_failures,
            'ssid': self.ssid,
            'mac_address': self.get_mac_address()
        }
    
    async def test_connectivity(self, host="8.8.8.8", port=53):
        """Test internet connectivity"""
        if not self.is_connected():
            return False
        
        try:
            # Simple socket connection test
            sock = self.socket_pool.socket(self.socket_pool.AF_INET, self.socket_pool.SOCK_STREAM)
            sock.settimeout(5)
            
            try:
                sock.connect((host, port))
                sock.close()
                return True
            except:
                return False
                
        except Exception as e:
            print(f"Connectivity test error: {e}")
            return False
    
    def get_connection_quality(self):
        """Get connection quality description"""
        if not self.is_connected():
            return "Disconnected"
        
        rssi = self.get_signal_strength()
        
        if rssi > -30:
            return "Excellent"
        elif rssi > -50:
            return "Good"
        elif rssi > -70:
            return "Fair"
        elif rssi > -90:
            return "Poor"
        else:
            return "Very Poor"
