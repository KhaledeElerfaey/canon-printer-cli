"""
Printer Discovery Module for Canon Printers using IPP
"""

import socket
import subprocess
import re
import time
from typing import List, Dict, Optional
import ipaddress
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from platform_utils import PlatformUtils


class CanonPrinterDiscovery:
    def __init__(self, config_manager=None):
        self.canon_keywords = [
            'canon', 'pixma', 'imageclass', 'maxify', 'selphy',
            'imagerunner', 'ij', 'mb', 'mx', 'mp', 'mg', 'mf'
        ]
        self.ipp_ports = [631, 9100, 8080, 80]
        self.platform = PlatformUtils()
        self.config_manager = config_manager
        
    def find_canon_printers(self) -> List[Dict]:
        """Find Canon printers using multiple discovery methods"""
        printers = []
        
        # Method 0: Include manually configured printers
        if self.config_manager:
            manual_printers = self._get_manual_printers()
            printers.extend(manual_printers)
        
        # Method 1: Use platform-specific system printer discovery
        system_printers = self.platform.get_system_printers()
        printers.extend(system_printers)
        
        # Method 2: Network scan for IPP printers (skip the IP of manual printers to avoid duplicates)
        network_printers = self._discover_network_printers()
        printers.extend(network_printers)
        
        # Method 3: Try Bonjour/mDNS discovery
        mdns_printers = self._discover_mdns_printers()
        printers.extend(mdns_printers)
        
        # Remove duplicates based on URI
        unique_printers = {}
        for printer in printers:
            if printer['uri'] not in unique_printers:
                unique_printers[printer['uri']] = printer
                
        return list(unique_printers.values())
        
    def _get_manual_printers(self) -> List[Dict]:
        """Get manually configured printers from config"""
        printers = []
        
        if not self.config_manager:
            return printers
            
        # Get all cached printers that were manually added
        for uri, printer_info in self.config_manager.printers_cache.items():
            if printer_info.get('manually_added', False):
                # Test if the printer is still reachable
                is_online = self.test_printer_connection(uri)
                
                printers.append({
                    'name': printer_info.get('name', 'Unknown Printer'),
                    'uri': uri,
                    'status': 'Available' if is_online else 'Offline',
                    'model': printer_info.get('model', 'Unknown'),
                    'source': 'manual_config',
                    'ip': printer_info.get('ip', ''),
                    'port': printer_info.get('port', 631)
                })
                
        return printers
        
    def _discover_system_printers(self) -> List[Dict]:
        """Discover printers using system commands"""
        printers = []
        
        try:
            # macOS: Use lpstat to list printers
            result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'printer' in line.lower():
                        # Parse printer name
                        match = re.search(r'printer (\S+)', line)
                        if match:
                            printer_name = match.group(1)
                            if self._is_canon_printer(printer_name):
                                # Get printer URI
                                uri = self._get_printer_uri(printer_name)
                                if uri:
                                    printers.append({
                                        'name': printer_name,
                                        'uri': uri,
                                        'status': 'Available',
                                        'model': self._extract_model(printer_name),
                                        'source': 'system'
                                    })
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
            
        return printers
        
    def _discover_network_printers(self) -> List[Dict]:
        """Discover Canon printers on the network using IPP port scanning"""
        printers = []
        network_ranges = self._get_network_ranges()
        
        print("🔍 Scanning network for Canon printers...")
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            
            for network in network_ranges:
                for ip in network:
                    future = executor.submit(self._scan_host_for_ipp, str(ip))
                    futures.append(future)
                    
            for future in as_completed(futures):
                printer = future.result()
                if printer:
                    printers.append(printer)
                    
        return printers
        
    def _discover_mdns_printers(self) -> List[Dict]:
        """Discover printers using mDNS/Bonjour"""
        printers = []
        
        try:
            # Try using dns-sd command (available on macOS)
            result = subprocess.run([
                'dns-sd', '-B', '_ipp._tcp'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                # Parse mDNS results (this is a simplified version)
                lines = result.stdout.split('\n')
                for line in lines:
                    if any(keyword in line.lower() for keyword in self.canon_keywords):
                        # Extract service information
                        parts = line.split()
                        if len(parts) >= 7:
                            service_name = parts[6]
                            if self._is_canon_printer(service_name):
                                printers.append({
                                    'name': service_name,
                                    'uri': f"ipp://{service_name}.local:631/ipp/print",
                                    'status': 'Available',
                                    'model': self._extract_model(service_name),
                                    'source': 'mdns'
                                })
                                
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
            
        return printers
        
    def _get_network_ranges(self) -> List[ipaddress.IPv4Network]:
        """Get local network ranges to scan"""
        networks = []
        
        try:
            # Get local network interfaces
            result = subprocess.run(['route', '-n', 'get', 'default'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                # Extract gateway IP
                for line in result.stdout.split('\n'):
                    if 'gateway:' in line:
                        gateway = line.split(':')[1].strip()
                        # Assume /24 network
                        network_base = '.'.join(gateway.split('.')[:-1]) + '.0/24'
                        networks.append(ipaddress.IPv4Network(network_base, strict=False))
                        break
        except Exception:
            # Fallback to common private networks
            common_networks = [
                '192.168.1.0/24',
                '192.168.0.0/24',
                '10.0.0.0/24',
                '172.16.0.0/24'
            ]
            networks = [ipaddress.IPv4Network(net) for net in common_networks]
            
        return networks
        
    def _scan_host_for_ipp(self, ip: str) -> Optional[Dict]:
        """Scan a single host for IPP services"""
        for port in self.ipp_ports:
            if self._is_port_open(ip, port):
                printer_info = self._get_ipp_printer_info(ip, port)
                if printer_info and self._is_canon_printer(printer_info.get('name', '')):
                    return {
                        'name': printer_info['name'],
                        'uri': f"ipp://{ip}:{port}/ipp/print",
                        'status': printer_info.get('status', 'Unknown'),
                        'model': printer_info.get('model', 'Unknown'),
                        'source': 'network_scan'
                    }
        return None
        
    def _is_port_open(self, ip: str, port: int, timeout: float = 1.0) -> bool:
        """Check if a port is open on the given IP"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, port))
                return result == 0
        except Exception:
            return False
            
    def _get_ipp_printer_info(self, ip: str, port: int) -> Optional[Dict]:
        """Get printer information using IPP"""
        try:
            # Try to get printer attributes using IPP
            # This is a simplified implementation
            import requests
            
            ipp_url = f"http://{ip}:{port}/ipp/print"
            
            # Try to get printer status page
            try:
                response = requests.get(f"http://{ip}:{port}", timeout=3)
                if response.status_code == 200:
                    content = response.text.lower()
                    
                    # Look for Canon indicators in the page
                    if any(keyword in content for keyword in self.canon_keywords):
                        # Extract printer name from content
                        name_match = re.search(r'<title>([^<]+)</title>', response.text, re.IGNORECASE)
                        name = name_match.group(1) if name_match else f"Canon Printer at {ip}"
                        
                        return {
                            'name': name,
                            'model': self._extract_model(name),
                            'status': 'Available'
                        }
            except:
                pass
                
        except Exception:
            pass
            
        return None
        
    def _is_canon_printer(self, name: str) -> bool:
        """Check if the printer name indicates it's a Canon printer"""
        name_lower = name.lower()
        return any(keyword in name_lower for keyword in self.canon_keywords)
        
    def _extract_model(self, name: str) -> str:
        """Extract Canon model from printer name"""
        name_upper = name.upper()
        
        # Common Canon model patterns
        patterns = [
            r'PIXMA\s+([A-Z]+\d+)',
            r'(MX\d+[A-Z]*)',
            r'(MP\d+[A-Z]*)',
            r'(MG\d+[A-Z]*)',
            r'(MF\d+[A-Z]*)',
            r'(MB\d+[A-Z]*)',
            r'IMAGECLASS\s+([A-Z]+\d+)',
            r'IMAGERUNNER\s+([A-Z]+\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, name_upper)
            if match:
                return f"Canon {match.group(0)}"
                
        return "Canon Printer"
        
    def _get_printer_uri(self, printer_name: str) -> Optional[str]:
        """Get printer URI using system commands"""
        try:
            # macOS: Use lpoptions to get printer URI
            result = subprocess.run(['lpoptions', '-p', printer_name], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'device-uri' in line:
                        uri_match = re.search(r'device-uri=(\S+)', line)
                        if uri_match:
                            return uri_match.group(1)
                            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
            
        return None
        
    def get_printer_capabilities(self, printer_uri: str) -> Dict:
        """Get printer capabilities using IPP"""
        capabilities = {
            'duplex': False,
            'color': False,
            'max_copies': 99,
            'supported_media': [],
            'supported_quality': ['draft', 'normal', 'high']
        }
        
        try:
            # This would implement IPP Get-Printer-Attributes operation
            # For now, return default capabilities for Canon printers
            capabilities.update({
                'duplex': True,  # Most Canon printers support duplex
                'color': True,   # Assume color support
                'supported_media': ['A4', 'Letter', 'Legal', '4x6', '5x7'],
            })
            
        except Exception:
            pass
            
        return capabilities
        
    def test_printer_connection(self, printer_uri: str) -> bool:
        """Test if we can connect to the printer"""
        try:
            # Parse URI to get host and port
            import urllib.parse
            parsed = urllib.parse.urlparse(printer_uri)
            
            host = parsed.hostname
            port = parsed.port or 631
            
            return self._is_port_open(host, port, timeout=5.0)
            
        except Exception:
            return False
