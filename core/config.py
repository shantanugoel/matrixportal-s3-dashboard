"""
Configuration management for MatrixPortal S3 Dashboard
Handles loading, saving, and validation of configuration data
"""
import json
import os

class ConfigManager:
    """Manages system configuration with atomic writes and validation"""
    
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config_backup = f"{config_file}.bak"
        self.default_config = self._get_default_config()
        
    def _get_default_config(self):
        """Get default configuration"""
        return {
            "system": {
                "wifi_ssid": "",
                "wifi_password": "",
                "display_brightness": 50,
                "rotation_interval": 5,
                "timezone": "UTC"
            },
            "display": {
                "width": 64,
                "height": 64,
                "bit_depth": 6,
                "brightness": {
                    "auto": False,
                    "manual": 0.5,
                    "day": 0.8,
                    "night": 0.2
                }
            },
            "network": {
                "timeout": 10,
                "retry_count": 3,
                "retry_delay": 5
            },
            "web": {
                "port": 80,
                "enabled": True
            },
            "plugins": {
                "clock": {
                    "enabled": True,
                    "display_seconds": True,
                    "format_24h": True
                }
            }
        }
    
    def load_config(self):
        """Load configuration from file with fallback to defaults"""
        try:
            # Try to open the config file
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            # Resolve environment variables in config
            config = self._resolve_env_vars(config)
            
            # Merge with defaults to ensure all keys exist
            merged_config = self._merge_configs(self.default_config, config)
            
            print(f"Configuration loaded from {self.config_file}")
            return merged_config
            
        except OSError:
            # File doesn't exist
            print(f"Config file not found, using defaults")
            return self.default_config.copy()
                
        except Exception as e:
            print(f"Error loading config: {e}")
            
            # Try backup file
            try:
                with open(self.config_backup, 'r') as f:
                    config = json.load(f)
                print(f"Loaded from backup: {self.config_backup}")
                return self._merge_configs(self.default_config, config)
            except OSError:
                # Backup file doesn't exist
                pass
            except Exception:
                # Backup file corrupted
                pass
            
            # Return defaults if all else fails
            print("Using default configuration")
            return self.default_config.copy()
    
    def save_config(self, config):
        """Save configuration to file with atomic write"""
        try:
            print("Starting config save process")
            # Create backup if original exists
            try:
                print("Attempting to create backup")
                os.rename(self.config_file, self.config_backup)
                print("Backup created successfully")
            except OSError as backup_err:
                print(f"Backup failed (normal if file doesn't exist): {backup_err}")
                # Original file doesn't exist, no need to backup
                pass
            
            # Write to temporary file first
            temp_file = f"{self.config_file}.tmp"
            print(f"Attempting to write to temp file: {temp_file}")
            with open(temp_file, 'w') as f:
                json.dump(config, f, indent=2)
            print("Temp file written successfully")
            
            # Atomic rename
            print(f"Attempting to rename {temp_file} to {self.config_file}")
            os.rename(temp_file, self.config_file)
            print("Rename successful")
            
            print(f"Configuration saved to {self.config_file}")
            return True
            
        except OSError as e:
            print(f"Error saving config: {e}")
            print(f"About to re-raise OSError: {e}")
            
            # Restore backup if it exists
            try:
                os.rename(self.config_backup, self.config_file)
            except OSError:
                # Backup file doesn't exist
                pass
            
            # Re-raise OSError so web server can handle it properly
            print("Re-raising OSError now")
            raise
            
        except Exception as e:
            print(f"Error saving config: {e}")
            
            # Restore backup if it exists
            try:
                os.rename(self.config_backup, self.config_file)
            except OSError:
                # Backup file doesn't exist
                pass
            
            return False
    
    def _merge_configs(self, default, user):
        """Recursively merge user config with defaults"""
        merged = default.copy()
        
        for key, value in user.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def _resolve_env_vars(self, config):
        """Recursively resolve environment variables in config"""
        import os
        
        if isinstance(config, dict):
            resolved = {}
            for key, value in config.items():
                resolved[key] = self._resolve_env_vars(value)
            return resolved
        elif isinstance(config, list):
            return [self._resolve_env_vars(item) for item in config]
        elif isinstance(config, str):
            # Check if string looks like an environment variable: ${VAR_NAME}
            if config.startswith('${') and config.endswith('}'):
                env_var = config[2:-1]  # Remove ${ and }
                env_value = os.getenv(env_var)
                if env_value is not None:
                    print(f"Resolved ${env_var} from environment")
                    return env_value
                else:
                    print(f"Warning: Environment variable {env_var} not found, using default")
                    return config
            return config
        else:
            return config
    
    def get_plugin_config(self, plugin_name):
        """Get configuration for a specific plugin"""
        config = self.load_config()
        return config.get('plugins', {}).get(plugin_name, {})
    
    def update_plugin_config(self, plugin_name, plugin_config):
        """Update configuration for a specific plugin"""
        config = self.load_config()
        
        if 'plugins' not in config:
            config['plugins'] = {}
        
        config['plugins'][plugin_name] = plugin_config
        
        return self.save_config(config)
    
    def validate_config(self, config):
        """Validate configuration structure"""
        try:
            # Check required top-level keys
            required_keys = ['system', 'display', 'network', 'web', 'plugins']
            
            for key in required_keys:
                if key not in config:
                    print(f"Missing required config key: {key}")
                    return False
            
            # Validate system config
            system = config['system']
            if not isinstance(system.get('rotation_interval'), (int, float)):
                print("Invalid rotation_interval")
                return False
            
            # Validate display config
            display = config['display']
            if not isinstance(display.get('width'), int) or display['width'] <= 0:
                print("Invalid display width")
                return False
            
            if not isinstance(display.get('height'), int) or display['height'] <= 0:
                print("Invalid display height")
                return False
            
            return True
            
        except Exception as e:
            print(f"Config validation error: {e}")
            return False
    
    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        return self.save_config(self.default_config)
    
    def get_config_size(self):
        """Get configuration file size in bytes"""
        try:
            stat = os.stat(self.config_file)
            return stat[6]  # st_size is at index 6 in CircuitPython
        except OSError:
            return 0
