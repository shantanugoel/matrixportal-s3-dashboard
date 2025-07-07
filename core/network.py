"""
Network management for MatrixPortal S3 Dashboard
Handles Wi-Fi connection, reconnection, and network reliability
"""
import wifi
import socketpool
import ssl
import time
import asyncio
try:
    import watchdog
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("Watchdog not available on this platform")

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
        self.last_watchdog_feed = time.monotonic()
        self.consecutive_failures = 0
        self.backoff_delay = self.retry_delay  # Start with base delay
        
        # Socket pool for reuse
        self.socket_pool = None
        self.ssl_context = None
        
        # Watchdog configuration
        self.watchdog_enabled = config.get('watchdog_enabled', True)
        self.watchdog_timeout = config.get('watchdog_timeout', 120)  # 2 minutes
        self.watchdog_feed_interval = config.get('watchdog_feed_interval', 30)  # 30 seconds
        
        # Captive portal configuration
        self.captive_portal_enabled = config.get('captive_portal_enabled', True)
        self.captive_portal_ssid = config.get('captive_portal_ssid', 'MatrixPortal-Setup')
        self.captive_portal_password = config.get('captive_portal_password', '')  # Open AP
        self.captive_portal_active = False
        self.captive_portal_timeout = config.get('captive_portal_timeout', 300)  # 5 minutes
        
        # Initialize watchdog if available
        self.watchdog = None
        if WATCHDOG_AVAILABLE and self.watchdog_enabled:
            try:
                self.watchdog = watchdog.WatchDogTimer(timeout=self.watchdog_timeout)
                print(f"Watchdog initialized with {self.watchdog_timeout}s timeout")
            except Exception as e:
                print(f"Failed to initialize watchdog: {e}")
                self.watchdog = None
        
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
        """Attempt to reconnect to Wi-Fi with exponential backoff"""
        current_time = time.monotonic()
        
        # Calculate backoff delay based on consecutive failures
        required_delay = min(self.backoff_delay, 300)  # Max 5 minutes
        
        # Don't attempt reconnection too frequently
        if current_time - self.last_connection_attempt < required_delay:
            return False
        
        print(f"Attempting Wi-Fi reconnection... (attempt {self.consecutive_failures + 1}, delay: {required_delay}s)")
        
        success = await self.connect()
        
        if success:
            # Reset backoff on successful connection
            self.consecutive_failures = 0
            self.backoff_delay = self.retry_delay
            print("Reconnection successful, backoff reset")
        else:
            # Increase backoff delay exponentially
            self.consecutive_failures += 1
            self.backoff_delay = min(self.backoff_delay * 2, 300)  # Max 5 minutes
            print(f"Reconnection failed, backoff increased to {self.backoff_delay}s")
        
        return success
    
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
            'connection_quality': self.get_connection_quality(),
            'connection_failures': self.connection_failures,
            'consecutive_failures': self.consecutive_failures,
            'backoff_delay': self.backoff_delay,
            'ssid': self.ssid,
            'mac_address': self.get_mac_address(),
            'watchdog': self.get_watchdog_status(),
            'captive_portal': {
                'enabled': self.captive_portal_enabled,
                'active': self.captive_portal_active,
                'ssid': self.captive_portal_ssid,
                'ip_address': self.get_captive_portal_ip()
            }
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
    
    def feed_watchdog(self):
        """Feed the watchdog to prevent system reset"""
        if self.watchdog:
            try:
                self.watchdog.feed()
                self.last_watchdog_feed = time.monotonic()
                print("Watchdog fed")
            except Exception as e:
                print(f"Error feeding watchdog: {e}")
    
    def check_watchdog_feed_needed(self):
        """Check if watchdog needs to be fed"""
        if not self.watchdog:
            return False
        
        time_since_last_feed = time.monotonic() - self.last_watchdog_feed
        return time_since_last_feed >= self.watchdog_feed_interval
    
    async def maintain_system_health(self):
        """Maintain system health - feed watchdog and check connectivity"""
        # Feed watchdog if needed
        if self.check_watchdog_feed_needed():
            self.feed_watchdog()
        
        # If captive portal is active, don't try to reconnect to WiFi
        if self.captive_portal_active:
            return
        
        # Check connectivity and reconnect if needed
        if not self.is_connected():
            print("Lost connectivity, attempting reconnection...")
            success = await self.reconnect()
            
            # If reconnection fails, check if we should start captive portal
            if not success:
                await self.check_captive_portal_fallback()
        
        # Test internet connectivity periodically
        if self.is_connected():
            connectivity_ok = await self.test_connectivity()
            if not connectivity_ok:
                print("Internet connectivity lost, attempting reconnection...")
                success = await self.reconnect()
                
                # If reconnection fails, check if we should start captive portal
                if not success:
                    await self.check_captive_portal_fallback()
    
    def enable_watchdog(self):
        """Enable watchdog monitoring"""
        if WATCHDOG_AVAILABLE and not self.watchdog:
            try:
                self.watchdog = watchdog.WatchDogTimer(timeout=self.watchdog_timeout)
                self.watchdog_enabled = True
                print("Watchdog enabled")
            except Exception as e:
                print(f"Failed to enable watchdog: {e}")
    
    def disable_watchdog(self):
        """Disable watchdog monitoring"""
        if self.watchdog:
            try:
                self.watchdog.deinit()
                self.watchdog = None
                self.watchdog_enabled = False
                print("Watchdog disabled")
            except Exception as e:
                print(f"Error disabling watchdog: {e}")
    
    def get_watchdog_status(self):
        """Get watchdog status information"""
        return {
            'watchdog_available': WATCHDOG_AVAILABLE,
            'watchdog_enabled': self.watchdog_enabled,
            'watchdog_active': self.watchdog is not None,
            'watchdog_timeout': self.watchdog_timeout,
            'last_feed': self.last_watchdog_feed,
            'time_since_feed': time.monotonic() - self.last_watchdog_feed,
            'feed_interval': self.watchdog_feed_interval
        }
    
    async def start_captive_portal(self):
        """Start captive portal access point for configuration"""
        if not self.captive_portal_enabled:
            print("Captive portal disabled in configuration")
            return False
        
        try:
            # Stop existing connections first
            if wifi.radio.connected:
                wifi.radio.stop_station()
            
            # Start access point
            print(f"Starting captive portal: {self.captive_portal_ssid}")
            
            if self.captive_portal_password:
                wifi.radio.start_ap(
                    ssid=self.captive_portal_ssid,
                    password=self.captive_portal_password
                )
            else:
                wifi.radio.start_ap(ssid=self.captive_portal_ssid)
            
            self.captive_portal_active = True
            self.connected = False  # Not connected to external network
            
            # Create socket pool for AP mode
            self.socket_pool = socketpool.SocketPool(wifi.radio)
            
            print(f"Captive portal active on {wifi.radio.ipv4_address_ap}")
            return True
            
        except Exception as e:
            print(f"Failed to start captive portal: {e}")
            self.captive_portal_active = False
            return False
    
    async def stop_captive_portal(self):
        """Stop captive portal and return to station mode"""
        try:
            if self.captive_portal_active:
                wifi.radio.stop_ap()
                self.captive_portal_active = False
                print("Captive portal stopped")
            
            # Reset socket pool
            self.socket_pool = None
            return True
            
        except Exception as e:
            print(f"Error stopping captive portal: {e}")
            return False
    
    def is_captive_portal_active(self):
        """Check if captive portal is currently active"""
        return self.captive_portal_active
    
    def get_captive_portal_ip(self):
        """Get captive portal IP address"""
        try:
            if self.captive_portal_active:
                return str(wifi.radio.ipv4_address_ap)
            return None
        except:
            return None
    
    async def check_captive_portal_fallback(self):
        """Check if captive portal fallback should be activated"""
        # Only activate if we have too many consecutive failures
        if (self.consecutive_failures >= 3 and 
            not self.captive_portal_active and 
            self.captive_portal_enabled):
            
            print("Multiple connection failures, starting captive portal...")
            await self.start_captive_portal()
            return True
        
        return False
    
    async def fetch_json(self, url, timeout=30):
        """Fetch JSON data from a URL with retry for EINPROGRESS"""
        if not self.is_connected() or not self.socket_pool:
            return None
            
        import adafruit_requests
        requests = adafruit_requests.Session(self.socket_pool, self.ssl_context)
        
        for attempt in range(3): # Try up to 3 times
            try:
                response = requests.get(url, timeout=timeout)
                
                if response.status_code == 200:
                    data = response.json()
                    response.close()
                    return data
                else:
                    print(f"HTTP error {response.status_code} for {url}")
                    response.close()
                    return None
            
            except OSError as e:
                if e.errno == 119: # EINPROGRESS
                    print(f"Network operation in progress, retrying... (attempt {attempt + 1})")
                    await asyncio.sleep(2) # Wait before retrying
                    continue
                else:
                    print(f"Unhandled OSError fetching {url}: {e}")
                    return None
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                return None
        
        print(f"Failed to fetch {url} after multiple retries.")
        return None
