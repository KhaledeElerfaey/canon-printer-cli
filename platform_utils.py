"""
Cross-platform utilities for Canon Printer CLI
Handles OS-specific functionality for Windows, macOS, and Linux
"""

import os
import sys
import platform
import subprocess
import socket
from typing import List, Dict, Optional, Tuple
import tempfile


class PlatformUtils:
    def __init__(self):
        self.os_name = platform.system().lower()
        self.is_windows = self.os_name == 'windows'
        self.is_macos = self.os_name == 'darwin'
        self.is_linux = self.os_name == 'linux'
        
    def get_system_printers(self) -> List[Dict]:
        """Get system printers using platform-specific methods"""
        if self.is_windows:
            return self._get_windows_printers()
        else:
            return self._get_unix_printers()
            
    def _get_windows_printers(self) -> List[Dict]:
        """Get printers on Windows using WMI"""
        printers = []
        
        try:
            import wmi
            c = wmi.WMI()
            
            for printer in c.Win32_Printer():
                if self._is_canon_printer(printer.Name):
                    printers.append({
                        'name': printer.Name,
                        'uri': self._windows_printer_to_uri(printer),
                        'status': self._get_windows_printer_status(printer),
                        'model': getattr(printer, 'DriverName', 'Unknown'),
                        'source': 'windows_wmi',
                        'location': getattr(printer, 'Location', ''),
                        'port': getattr(printer, 'PortName', ''),
                        'shared': getattr(printer, 'Shared', False)
                    })
                    
        except ImportError:
            # Fallback: use PowerShell
            printers.extend(self._get_windows_printers_powershell())
        except Exception as e:
            print(f"Warning: Error getting Windows printers: {e}")
            
        return printers
        
    def _get_windows_printers_powershell(self) -> List[Dict]:
        """Get Windows printers using PowerShell as fallback"""
        printers = []
        
        try:
            # PowerShell command to get printers
            cmd = [
                'powershell', '-Command', 
                'Get-Printer | Select-Name,DriverName,PortName,Shared,PrinterStatus | ConvertTo-Json'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                import json
                printer_data = json.loads(result.stdout)
                
                # Handle single printer vs array
                if isinstance(printer_data, dict):
                    printer_data = [printer_data]
                    
                for printer in printer_data:
                    if self._is_canon_printer(printer.get('Name', '')):
                        printers.append({
                            'name': printer.get('Name', ''),
                            'uri': f"windows-printer://{printer.get('Name', '')}",
                            'status': self._map_windows_status(printer.get('PrinterStatus', 0)),
                            'model': printer.get('DriverName', 'Unknown'),
                            'source': 'windows_powershell',
                            'port': printer.get('PortName', ''),
                            'shared': printer.get('Shared', False)
                        })
                        
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception) as e:
            print(f"Warning: PowerShell printer discovery failed: {e}")
            
        return printers
        
    def _get_unix_printers(self) -> List[Dict]:
        """Get printers on Unix-like systems (macOS/Linux)"""
        printers = []
        
        try:
            # Try using CUPS Python bindings first
            try:
                import cups
                conn = cups.Connection()
                cups_printers = conn.getPrinters()
                
                for name, info in cups_printers.items():
                    if self._is_canon_printer(name):
                        printers.append({
                            'name': name,
                            'uri': info.get('device-uri', f'cups://{name}'),
                            'status': self._map_cups_status(info.get('printer-state', 3)),
                            'model': info.get('printer-make-and-model', 'Unknown'),
                            'source': 'cups_python',
                            'location': info.get('printer-location', ''),
                            'description': info.get('printer-info', '')
                        })
                        
            except ImportError:
                # Fallback to lpstat command
                printers.extend(self._get_unix_printers_lpstat())
                
        except Exception as e:
            print(f"Warning: Error getting Unix printers: {e}")
            
        return printers
        
    def _get_unix_printers_lpstat(self) -> List[Dict]:
        """Get Unix printers using lpstat command"""
        printers = []
        
        try:
            result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'printer' in line.lower():
                        import re
                        match = re.search(r'printer (\S+)', line)
                        if match:
                            printer_name = match.group(1)
                            if self._is_canon_printer(printer_name):
                                uri = self._get_printer_uri_lpstat(printer_name)
                                printers.append({
                                    'name': printer_name,
                                    'uri': uri or f'cups://{printer_name}',
                                    'status': 'Available',
                                    'model': self._extract_model(printer_name),
                                    'source': 'lpstat'
                                })
                                
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
            
        return printers
        
    def print_file(self, file_path: str, printer_name: str, options: Dict = None) -> bool:
        """Print file using platform-specific method"""
        if self.is_windows:
            return self._print_file_windows(file_path, printer_name, options)
        else:
            return self._print_file_unix(file_path, printer_name, options)
            
    def _print_file_windows(self, file_path: str, printer_name: str, options: Dict = None) -> bool:
        """Print file on Windows"""
        options = options or {}
        
        try:
            # Method 1: Try using win32print
            try:
                import win32print
                import win32api
                
                # Open printer
                printer_handle = win32print.OpenPrinter(printer_name)
                
                try:
                    # Start print job
                    job_info = ("Python Print Job", None, "RAW")
                    job_id = win32print.StartDocPrinter(printer_handle, 1, job_info)
                    
                    try:
                        win32print.StartPagePrinter(printer_handle)
                        
                        # Read and send file data
                        with open(file_path, 'rb') as f:
                            data = f.read()
                            win32print.WritePrinter(printer_handle, data)
                            
                        win32print.EndPagePrinter(printer_handle)
                        win32print.EndDocPrinter(printer_handle)
                        
                        return True
                        
                    finally:
                        if job_id:
                            pass  # Job cleanup handled by EndDocPrinter
                            
                finally:
                    win32print.ClosePrinter(printer_handle)
                    
            except ImportError:
                # Method 2: Use PowerShell
                return self._print_file_windows_powershell(file_path, printer_name, options)
                
        except Exception as e:
            print(f"Error printing on Windows: {e}")
            # Method 3: Try opening with default application
            try:
                os.startfile(file_path, "print")
                return True
            except Exception:
                return False
                
    def _print_file_windows_powershell(self, file_path: str, printer_name: str, options: Dict) -> bool:
        """Print file on Windows using PowerShell"""
        try:
            # Build PowerShell command
            ps_script = f"""
            $printer = Get-Printer -Name '{printer_name}'
            if ($printer) {{
                Start-Process -FilePath '{file_path}' -Verb Print -WindowStyle Hidden
            }} else {{
                Write-Error "Printer not found"
            }}
            """
            
            cmd = ['powershell', '-Command', ps_script]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"PowerShell print failed: {e}")
            return False
            
    def _print_file_unix(self, file_path: str, printer_name: str, options: Dict = None) -> bool:
        """Print file on Unix-like systems"""
        options = options or {}
        
        try:
            # Build lpr command
            cmd = ['lpr', '-P', printer_name]
            
            # Add options
            if options.get('copies', 1) > 1:
                cmd.extend(['-#', str(options['copies'])])
                
            lpr_options = []
            if options.get('duplex'):
                lpr_options.append('sides=two-sided-long-edge')
                
            quality = options.get('quality', 'normal')
            if quality == 'draft':
                lpr_options.append('print-quality=3')
            elif quality == 'high':
                lpr_options.append('print-quality=5')
            else:
                lpr_options.append('print-quality=4')
                
            if lpr_options:
                cmd.extend(['-o', ','.join(lpr_options)])
                
            cmd.append(file_path)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0
            
        except Exception as e:
            print(f"Unix print failed: {e}")
            return False
            
    def get_network_interfaces(self) -> List[str]:
        """Get local network interface IP addresses"""
        interfaces = []
        
        try:
            if self.is_windows:
                # Windows: Use ipconfig
                result = subprocess.run(['ipconfig'], capture_output=True, text=True)
                if result.returncode == 0:
                    import re
                    for line in result.stdout.split('\n'):
                        match = re.search(r'IPv4 Address.*: (\d+\.\d+\.\d+\.\d+)', line)
                        if match:
                            ip = match.group(1)
                            if not ip.startswith('127.'):
                                interfaces.append(ip)
            else:
                # Unix: Use hostname or ip command
                try:
                    result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
                    if result.returncode == 0:
                        interfaces = [ip.strip() for ip in result.stdout.split() 
                                    if not ip.startswith('127.')]
                except FileNotFoundError:
                    # Fallback for systems without hostname -I
                    import socket
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    interfaces.append(s.getsockname()[0])
                    s.close()
                    
        except Exception:
            pass
            
        return interfaces
        
    def _is_canon_printer(self, name: str) -> bool:
        """Check if printer name indicates it's a Canon printer"""
        canon_keywords = [
            'canon', 'pixma', 'imageclass', 'maxify', 'selphy',
            'imagerunner', 'ij', 'mb', 'mx', 'mp', 'mg', 'mf'
        ]
        name_lower = name.lower()
        return any(keyword in name_lower for keyword in canon_keywords)
        
    def _extract_model(self, name: str) -> str:
        """Extract Canon model from printer name"""
        name_upper = name.upper()
        
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
        
        import re
        for pattern in patterns:
            match = re.search(pattern, name_upper)
            if match:
                return f"Canon {match.group(0)}"
                
        return "Canon Printer"
        
    def _windows_printer_to_uri(self, printer) -> str:
        """Convert Windows printer object to URI"""
        port_name = getattr(printer, 'PortName', '')
        
        # Check if it's a network printer
        if port_name.startswith('IP_'):
            ip = port_name.replace('IP_', '').replace('_', '.')
            return f"ipp://{ip}:631/ipp/print"
        elif '\\\\' in port_name:
            return f"smb://{port_name}"
        else:
            return f"windows-printer://{printer.Name}"
            
    def _get_windows_printer_status(self, printer) -> str:
        """Get Windows printer status"""
        status_map = {
            0: 'Ready',
            1: 'Paused',
            2: 'Error',
            3: 'Pending Deletion',
            4: 'Paper Jam',
            5: 'Paper Out',
            6: 'Manual Feed',
            7: 'Paper Problem',
            8: 'Offline',
            9: 'I/O Active',
            10: 'Busy',
            11: 'Printing',
            12: 'Output Bin Full',
            13: 'Not Available',
            14: 'Waiting',
            15: 'Processing',
            16: 'Initialization',
            17: 'Warming Up',
            18: 'Toner Low',
            19: 'No Toner',
            20: 'Page Punt',
            21: 'User Intervention Required',
            22: 'Out of Memory',
            23: 'Door Open'
        }
        
        status = getattr(printer, 'PrinterStatus', 0)
        return status_map.get(status, f'Unknown ({status})')
        
    def _map_windows_status(self, status_code: int) -> str:
        """Map Windows printer status code to string"""
        status_map = {
            1: 'Other',
            2: 'Unknown', 
            3: 'Idle',
            4: 'Printing',
            5: 'Warmup'
        }
        return status_map.get(status_code, 'Unknown')
        
    def _map_cups_status(self, status_code: int) -> str:
        """Map CUPS printer status to string"""
        status_map = {
            3: 'Idle',
            4: 'Printing',
            5: 'Stopped'
        }
        return status_map.get(status_code, 'Unknown')
        
    def _get_printer_uri_lpstat(self, printer_name: str) -> Optional[str]:
        """Get printer URI using lpstat"""
        try:
            result = subprocess.run(['lpoptions', '-p', printer_name], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                import re
                for line in result.stdout.split('\n'):
                    if 'device-uri' in line:
                        match = re.search(r'device-uri=(\S+)', line)
                        if match:
                            return match.group(1)
                            
        except Exception:
            pass
            
        return None
        
    def open_file_for_printing(self, file_path: str) -> bool:
        """Open file with system default application for printing"""
        try:
            if self.is_windows:
                os.startfile(file_path, "print")
            elif self.is_macos:
                subprocess.run(['open', '-a', 'Preview', file_path])
            else:  # Linux
                subprocess.run(['xdg-open', file_path])
            return True
        except Exception:
            return False
            
    def get_temp_dir(self) -> str:
        """Get platform-appropriate temporary directory"""
        return tempfile.gettempdir()
        
    def make_executable(self, file_path: str):
        """Make file executable (Unix only)"""
        if not self.is_windows:
            try:
                import stat
                st = os.stat(file_path)
                os.chmod(file_path, st.st_mode | stat.S_IEXEC)
            except Exception:
                pass
