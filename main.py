#!/usr/bin/env python3
"""
Canon Printer CLI - A Python CLI tool for printing documents to Canon printers via IPP
Author: Generated CLI Tool
"""

import argparse
import sys
import os
from pathlib import Path
from typing import List, Optional

from printer_discovery import CanonPrinterDiscovery
from document_handler import DocumentHandler
from config_manager import ConfigManager


class CanonPrinterCLI:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.printer_discovery = CanonPrinterDiscovery(self.config_manager)
        self.document_handler = DocumentHandler()
        
    def discover_printers(self) -> List[dict]:
        """Discover Canon printers on the network"""
        print("🔍 Discovering Canon printers on the network...")
        printers = self.printer_discovery.find_canon_printers()
        
        if not printers:
            print("❌ No Canon printers found on the network")
            return []
            
        print(f"✅ Found {len(printers)} Canon printer(s):")
        for i, printer in enumerate(printers, 1):
            print(f"  {i}. {printer['name']} - {printer['uri']}")
            
        return printers
        
    def print_document(self, file_path: str, printer_uri: Optional[str] = None, 
                      copies: int = 1, duplex: bool = False, quality: str = 'normal'):
        """Print a document to the specified printer"""
        
        # Validate file exists
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return False
            
        # Get printer URI if not provided
        if not printer_uri:
            printers = self.discover_printers()
            if not printers:
                return False
                
            if len(printers) == 1:
                printer_uri = printers[0]['uri']
                print(f"📄 Using printer: {printers[0]['name']}")
            else:
                # Let user select printer
                while True:
                    try:
                        choice = int(input("Select printer number: ")) - 1
                        if 0 <= choice < len(printers):
                            printer_uri = printers[choice]['uri']
                            print(f"📄 Using printer: {printers[choice]['name']}")
                            break
                        else:
                            print("Invalid choice. Please try again.")
                    except (ValueError, KeyboardInterrupt):
                        print("\nOperation cancelled.")
                        return False
                        
        # Print the document
        try:
            print(f"🖨️  Printing {file_path}...")
            result = self.document_handler.print_document(
                file_path, printer_uri, copies, duplex, quality
            )
            
            if result:
                print("✅ Document sent to printer successfully!")
                return True
            else:
                print("❌ Failed to print document")
                return False
                
        except Exception as e:
            print(f"❌ Error printing document: {str(e)}")
            return False
            
    def list_printers(self):
        """List all discovered Canon printers"""
        printers = self.discover_printers()
        if printers:
            print("\n📊 Printer Details:")
            for printer in printers:
                print(f"\nName: {printer['name']}")
                print(f"URI: {printer['uri']}")
                print(f"Status: {printer.get('status', 'Unknown')}")
                print(f"Model: {printer.get('model', 'Unknown')}")
                
    def print_test_page(self, printer_uri: Optional[str] = None):
        """Print a test page"""
        # Create a simple test document
        test_content = """
        CANON PRINTER TEST PAGE
        ======================
        
        Date: {date}
        Time: {time}
        
        This is a test page to verify your Canon printer is working correctly.
        
        Text Quality Test:
        - Regular text
        - Bold text (simulated with capitals: BOLD TEXT)
        - Different sizes and formatting
        
        If you can read this clearly, your printer is working properly!
        
        Color Test (if color printer):
        Red | Green | Blue | Yellow | Magenta | Cyan
        
        End of test page.
        """.format(
            date=__import__('datetime').datetime.now().strftime('%Y-%m-%d'),
            time=__import__('datetime').datetime.now().strftime('%H:%M:%S')
        )
        
        # Create temporary test file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_content)
            test_file = f.name
            
        try:
            result = self.print_document(test_file, printer_uri)
            return result
        finally:
            # Clean up temporary file
            os.unlink(test_file)
            
    def add_printer(self, ip: str, name: Optional[str] = None, port: int = 631, test_connection: bool = False) -> bool:
        """Manually add a Canon printer by IP address"""
        import re
        import requests
        
        # Validate IP address format
        ip_pattern = r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$'
        if not re.match(ip_pattern, ip):
            print(f"❌ Invalid IP address format: {ip}")
            return False
            
        print(f"🔗 Adding Canon printer at {ip}:{port}...")
        
        # Test connection first
        if not self.printer_discovery._is_port_open(ip, port, timeout=5.0):
            print(f"❌ Cannot connect to {ip}:{port}")
            print("   - Make sure the printer is powered on")
            print("   - Check if the IP address is correct")
            print("   - Verify network connectivity")
            return False
            
        print(f"✅ Connection successful to {ip}:{port}")
        
        # Try to get printer information
        printer_info = self.printer_discovery._get_ipp_printer_info(ip, port)
        
        if not printer_info:
            print("⚠️  Could not retrieve printer information via IPP")
            # Try to get basic info from web interface
            try:
                response = requests.get(f"http://{ip}:{port if port != 631 else 80}", timeout=5)
                if response.status_code == 200:
                    content = response.text.lower()
                    if any(keyword in content for keyword in ['canon', 'pixma', 'imageclass']):
                        print("✅ Detected Canon printer via web interface")
                        printer_info = {
                            'name': name or f"Canon Printer at {ip}",
                            'model': 'Unknown Canon Model',
                            'status': 'Available'
                        }
                    else:
                        print("⚠️  Device found but may not be a Canon printer")
                        printer_info = {
                            'name': name or f"Printer at {ip}",
                            'model': 'Unknown',
                            'status': 'Available'
                        }
            except:
                print("⚠️  Could not verify printer type")
                printer_info = {
                    'name': name or f"Printer at {ip}",
                    'model': 'Unknown',
                    'status': 'Available'
                }
        
        # Create printer URI
        printer_uri = f"ipp://{ip}:{port}/ipp/print"
        
        # Update printer name if custom name provided
        if name:
            printer_info['name'] = name
            
        # Save printer to configuration
        self.config_manager.save_printer_info(printer_uri, {
            'name': printer_info['name'],
            'model': printer_info.get('model', 'Unknown'),
            'status': printer_info.get('status', 'Available'),
            'ip': ip,
            'port': port,
            'manually_added': True,
            'capabilities': self.printer_discovery.get_printer_capabilities(printer_uri)
        })
        
        print(f"✅ Added printer: {printer_info['name']}")
        print(f"   URI: {printer_uri}")
        print(f"   Model: {printer_info.get('model', 'Unknown')}")
        
        # Test print if requested
        if test_connection:
            print("\n🧪 Testing printer connection...")
            return self.print_test_page(printer_uri)
            
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Canon Printer CLI - Print documents to Canon printers via IPP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s print document.pdf                    # Print PDF with default settings
  %(prog)s print photo.jpg -c 2 --quality high  # Print 2 copies in high quality
  %(prog)s print report.pdf --duplex             # Print double-sided
  %(prog)s discover                              # Discover Canon printers
  %(prog)s test                                  # Print a test page
  %(prog)s list                                  # List all discovered printers
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Print command
    print_parser = subparsers.add_parser('print', help='Print a document')
    print_parser.add_argument('file', help='Path to the document to print')
    print_parser.add_argument('-p', '--printer', help='Printer URI (if not specified, will auto-discover)')
    print_parser.add_argument('-c', '--copies', type=int, default=1, help='Number of copies (default: 1)')
    print_parser.add_argument('-d', '--duplex', action='store_true', help='Print double-sided')
    print_parser.add_argument('-q', '--quality', choices=['draft', 'normal', 'high'], 
                            default='normal', help='Print quality (default: normal)')
    
    # Discover command
    subparsers.add_parser('discover', help='Discover Canon printers on the network')
    
    # List command
    subparsers.add_parser('list', help='List all discovered Canon printers with details')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Print a test page')
    test_parser.add_argument('-p', '--printer', help='Printer URI (if not specified, will auto-discover)')
    
    # Add printer command
    add_parser = subparsers.add_parser('add', help='Manually add a Canon printer by IP address')
    add_parser.add_argument('ip', help='IP address of the Canon printer')
    add_parser.add_argument('-n', '--name', help='Custom name for the printer (optional)')
    add_parser.add_argument('-p', '--port', type=int, default=631, help='Port number (default: 631 for IPP)')
    add_parser.add_argument('--test', action='store_true', help='Test connection after adding')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
        
    cli = CanonPrinterCLI()
    
    try:
        if args.command == 'print':
            success = cli.print_document(
                args.file, args.printer, args.copies, args.duplex, args.quality
            )
            sys.exit(0 if success else 1)
            
        elif args.command == 'discover':
            cli.discover_printers()
            
        elif args.command == 'list':
            cli.list_printers()
            
        elif args.command == 'test':
            success = cli.print_test_page(args.printer)
            sys.exit(0 if success else 1)
            
        elif args.command == 'add':
            success = cli.add_printer(args.ip, args.name, args.port, args.test)
            sys.exit(0 if success else 1)
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
