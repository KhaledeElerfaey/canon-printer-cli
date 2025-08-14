"""
Configuration Manager for Canon Printer CLI
Handles user preferences, printer settings, and configuration persistence
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    def __init__(self, config_dir: Optional[str] = None):
        # Default config directory
        if config_dir is None:
            config_dir = os.path.expanduser("~/.canon-printer-cli")
            
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "config.yaml"
        self.printers_file = self.config_dir / "printers.json"
        
        # Default configuration
        self.default_config = {
            'default_printer': None,
            'default_copies': 1,
            'default_duplex': False,
            'default_quality': 'normal',
            'network_timeout': 5.0,
            'discovery_timeout': 30,
            'auto_discover': True,
            'save_printer_history': True,
            'preferred_paper_size': 'A4',
            'color_mode': 'auto',  # auto, color, mono
            'print_preview': False,
            'logging': {
                'enabled': True,
                'level': 'INFO',
                'file': str(self.config_dir / "canon-printer.log")
            },
            'network': {
                'scan_ranges': ['192.168.1.0/24', '192.168.0.0/24', '10.0.0.0/24'],
                'ports': [631, 9100, 8080, 80],
                'max_workers': 50
            }
        }
        
        self.config = {}
        self.printers_cache = {}
        
        # Create config directory and load config
        self._ensure_config_dir()
        self._load_config()
        self._load_printers_cache()
        
    def _ensure_config_dir(self):
        """Ensure configuration directory exists"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = yaml.safe_load(f) or {}
                    
                # Merge with defaults
                self.config = self._deep_merge(self.default_config.copy(), loaded_config)
                
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
                self.config = self.default_config.copy()
        else:
            self.config = self.default_config.copy()
            self._save_config()
            
    def _load_printers_cache(self):
        """Load cached printer information"""
        if self.printers_file.exists():
            try:
                with open(self.printers_file, 'r') as f:
                    self.printers_cache = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load printers cache: {e}")
                self.printers_cache = {}
        else:
            self.printers_cache = {}
            
    def _save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config: {e}")
            
    def _save_printers_cache(self):
        """Save printers cache to file"""
        try:
            with open(self.printers_file, 'w') as f:
                json.dump(self.printers_cache, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save printers cache: {e}")
            
    def _deep_merge(self, dict1: Dict, dict2: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with dot notation support"""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
            
    def set(self, key: str, value: Any, save: bool = True):
        """Set configuration value with dot notation support"""
        keys = key.split('.')
        config = self.config
        
        # Navigate to the parent dictionary
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        # Set the value
        config[keys[-1]] = value
        
        if save:
            self._save_config()
            
    def get_default_printer(self) -> Optional[str]:
        """Get the default printer URI"""
        return self.get('default_printer')
        
    def set_default_printer(self, printer_uri: str):
        """Set the default printer URI"""
        self.set('default_printer', printer_uri)
        
    def get_printer_settings(self, printer_uri: str) -> Dict[str, Any]:
        """Get settings for a specific printer"""
        return self.printers_cache.get(printer_uri, {
            'name': 'Unknown Canon Printer',
            'model': 'Unknown',
            'capabilities': {},
            'last_used': None,
            'usage_count': 0,
            'preferred_settings': {
                'quality': self.get('default_quality'),
                'duplex': self.get('default_duplex'),
                'copies': self.get('default_copies')
            }
        })
        
    def save_printer_info(self, printer_uri: str, printer_info: Dict[str, Any]):
        """Save printer information to cache"""
        if not self.get('save_printer_history'):
            return
            
        import datetime
        
        existing = self.printers_cache.get(printer_uri, {})
        existing.update({
            'name': printer_info.get('name', existing.get('name', 'Unknown')),
            'model': printer_info.get('model', existing.get('model', 'Unknown')),
            'status': printer_info.get('status', 'Unknown'),
            'last_seen': datetime.datetime.now().isoformat(),
            'capabilities': printer_info.get('capabilities', existing.get('capabilities', {}))
        })
        
        self.printers_cache[printer_uri] = existing
        self._save_printers_cache()
        
    def record_print_job(self, printer_uri: str, file_path: str, settings: Dict[str, Any]):
        """Record a print job for statistics and preferences"""
        if not self.get('save_printer_history'):
            return
            
        import datetime
        
        printer_info = self.printers_cache.get(printer_uri, {})
        printer_info['last_used'] = datetime.datetime.now().isoformat()
        printer_info['usage_count'] = printer_info.get('usage_count', 0) + 1
        
        # Update preferred settings based on usage
        preferred = printer_info.get('preferred_settings', {})
        if settings.get('quality'):
            preferred['quality'] = settings['quality']
        if 'duplex' in settings:
            preferred['duplex'] = settings['duplex']
        if settings.get('copies', 1) > 1:
            preferred['copies'] = settings['copies']
            
        printer_info['preferred_settings'] = preferred
        self.printers_cache[printer_uri] = printer_info
        self._save_printers_cache()
        
    def get_recently_used_printers(self, limit: int = 5) -> list:
        """Get recently used printers"""
        printers = []
        
        for uri, info in self.printers_cache.items():
            if 'last_used' in info:
                printers.append({
                    'uri': uri,
                    'name': info.get('name', 'Unknown'),
                    'last_used': info['last_used'],
                    'usage_count': info.get('usage_count', 0)
                })
                
        # Sort by last used, then by usage count
        printers.sort(key=lambda x: (x['last_used'], x['usage_count']), reverse=True)
        
        return printers[:limit]
        
    def get_network_config(self) -> Dict[str, Any]:
        """Get network scanning configuration"""
        return self.get('network', {})
        
    def update_network_config(self, config: Dict[str, Any]):
        """Update network scanning configuration"""
        current = self.get('network', {})
        current.update(config)
        self.set('network', current)
        
    def reset_to_defaults(self):
        """Reset configuration to default values"""
        self.config = self.default_config.copy()
        self._save_config()
        
    def export_config(self, export_path: str):
        """Export configuration to a file"""
        export_data = {
            'config': self.config,
            'printers_cache': self.printers_cache
        }
        
        try:
            with open(export_path, 'w') as f:
                if export_path.endswith('.json'):
                    json.dump(export_data, f, indent=2)
                else:
                    yaml.dump(export_data, f, default_flow_style=False, indent=2)
                    
            print(f"Configuration exported to {export_path}")
            
        except Exception as e:
            print(f"Error exporting configuration: {e}")
            
    def import_config(self, import_path: str):
        """Import configuration from a file"""
        try:
            with open(import_path, 'r') as f:
                if import_path.endswith('.json'):
                    data = json.load(f)
                else:
                    data = yaml.safe_load(f)
                    
            if 'config' in data:
                self.config = self._deep_merge(self.default_config.copy(), data['config'])
                self._save_config()
                
            if 'printers_cache' in data:
                self.printers_cache.update(data['printers_cache'])
                self._save_printers_cache()
                
            print(f"Configuration imported from {import_path}")
            
        except Exception as e:
            print(f"Error importing configuration: {e}")
            
    def show_config(self):
        """Display current configuration"""
        print("Current Configuration:")
        print("=" * 50)
        
        # Print main settings
        print(f"Default Printer: {self.get('default_printer', 'None')}")
        print(f"Default Copies: {self.get('default_copies')}")
        print(f"Default Duplex: {self.get('default_duplex')}")
        print(f"Default Quality: {self.get('default_quality')}")
        print(f"Auto Discovery: {self.get('auto_discover')}")
        
        print("\nNetwork Settings:")
        network = self.get('network', {})
        print(f"  Scan Ranges: {network.get('scan_ranges', [])}")
        print(f"  Ports: {network.get('ports', [])}")
        print(f"  Max Workers: {network.get('max_workers', 50)}")
        
        print(f"\nCached Printers: {len(self.printers_cache)}")
        if self.printers_cache:
            for uri, info in list(self.printers_cache.items())[:3]:  # Show first 3
                print(f"  - {info.get('name', 'Unknown')} ({uri})")
                
    def cleanup_old_cache(self, days: int = 30):
        """Clean up old printer cache entries"""
        import datetime
        
        cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
        removed = 0
        
        for uri in list(self.printers_cache.keys()):
            info = self.printers_cache[uri]
            last_seen_str = info.get('last_seen') or info.get('last_used')
            
            if last_seen_str:
                try:
                    last_seen = datetime.datetime.fromisoformat(last_seen_str)
                    if last_seen < cutoff:
                        del self.printers_cache[uri]
                        removed += 1
                except ValueError:
                    # Invalid date format, remove entry
                    del self.printers_cache[uri]
                    removed += 1
                    
        if removed > 0:
            self._save_printers_cache()
            print(f"Cleaned up {removed} old printer cache entries")
            
        return removed
