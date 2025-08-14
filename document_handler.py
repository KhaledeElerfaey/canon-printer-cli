"""
Document Handler Module for Canon Printer CLI
Handles different document types and printing via IPP
"""

import os
import mimetypes
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import urllib.parse
from platform_utils import PlatformUtils


class DocumentHandler:
    def __init__(self):
        self.platform = PlatformUtils()
        self.supported_formats = {
            'application/pdf': self._handle_pdf,
            'text/plain': self._handle_text,
            'image/jpeg': self._handle_image,
            'image/png': self._handle_image,
            'image/gif': self._handle_image,
            'image/tiff': self._handle_image,
            'application/postscript': self._handle_postscript,
            'application/msword': self._handle_office_doc,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': self._handle_office_doc,
            'application/vnd.ms-excel': self._handle_office_doc,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': self._handle_office_doc,
        }
        
    def print_document(self, file_path: str, printer_uri: str, copies: int = 1, 
                      duplex: bool = False, quality: str = 'normal') -> bool:
        """Print a document to the specified printer via IPP"""
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # Detect file type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            # Try to detect by extension
            ext = Path(file_path).suffix.lower()
            mime_type = self._get_mime_by_extension(ext)
            
        if not mime_type or mime_type not in self.supported_formats:
            return self._handle_generic_file(file_path, printer_uri, copies, duplex, quality)
            
        # Process the document using the appropriate handler
        try:
            processed_file = self.supported_formats[mime_type](file_path)
            if not processed_file:
                return False
                
            # Send to printer
            return self._send_to_printer(processed_file, printer_uri, copies, duplex, quality)
            
        except Exception as e:
            print(f"Error processing document: {str(e)}")
            return False
            
    def _handle_pdf(self, file_path: str) -> str:
        """Handle PDF files - they can be printed directly"""
        return file_path
        
    def _handle_text(self, file_path: str) -> str:
        """Handle plain text files"""
        # Text files can usually be printed directly, but let's ensure proper formatting
        try:
            # Read and reformat if needed
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Create a temporary formatted file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            temp_file.write(content)
            temp_file.close()
            
            return temp_file.name
            
        except Exception as e:
            print(f"Error processing text file: {str(e)}")
            return file_path  # Return original file as fallback
            
    def _handle_image(self, file_path: str) -> str:
        """Handle image files"""
        # Images can usually be printed directly
        return file_path
        
    def _handle_postscript(self, file_path: str) -> str:
        """Handle PostScript files"""
        return file_path
        
    def _handle_office_doc(self, file_path: str) -> Optional[str]:
        """Handle Microsoft Office documents by converting to PDF"""
        try:
            # Try to convert using LibreOffice (if available)
            temp_dir = tempfile.mkdtemp()
            
            # LibreOffice command to convert to PDF
            cmd = [
                'libreoffice', '--headless', '--convert-to', 'pdf',
                '--outdir', temp_dir, file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Find the generated PDF
                pdf_name = Path(file_path).stem + '.pdf'
                pdf_path = os.path.join(temp_dir, pdf_name)
                
                if os.path.exists(pdf_path):
                    return pdf_path
                    
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
            
        # Fallback: try using system's default application to print
        print("Warning: Could not convert Office document. Attempting direct print...")
        return file_path
        
    def _handle_generic_file(self, file_path: str, printer_uri: str, copies: int, 
                           duplex: bool, quality: str) -> bool:
        """Handle unsupported file types by trying system print commands"""
        try:
            return self._send_to_printer(file_path, printer_uri, copies, duplex, quality)
        except Exception as e:
            print(f"Error printing generic file: {str(e)}")
            return False
            
    def _send_to_printer(self, file_path: str, printer_uri: str, copies: int, 
                        duplex: bool, quality: str) -> bool:
        """Send file to printer using platform-specific methods"""
        try:
            # First try direct IPP printing
            if printer_uri.startswith(('ipp://', 'ipps://')):
                success = self._print_via_ipp(file_path, printer_uri, copies, duplex, quality)
                if success:
                    return True
            
            # Extract printer name from URI for system printer methods
            printer_name = self._extract_printer_name(printer_uri)
            
            # Prepare print options
            options = {
                'copies': copies,
                'duplex': duplex,
                'quality': quality
            }
            
            # Use platform-specific printing
            success = self.platform.print_file(file_path, printer_name or printer_uri, options)
            
            if not success:
                # Fallback: try alternative method
                return self._alternative_print_method(file_path, printer_uri, copies, duplex, quality)
                
            return success
            
        except Exception as e:
            print(f"Error sending to printer: {str(e)}")
            return self._alternative_print_method(file_path, printer_uri, copies, duplex, quality)
    
    def _print_via_ipp(self, file_path: str, printer_uri: str, copies: int, 
                      duplex: bool, quality: str) -> bool:
        """Print directly to IPP printer using proper protocols"""
        try:
            # Parse the IPP URI to get host and port
            parsed = urllib.parse.urlparse(printer_uri)
            host = parsed.hostname
            port = parsed.port or 631
            
            print(f"Sending print job to {host}:{port}...")
            
            # Method 1: Use enscript to convert text to PostScript, then print
            if file_path.endswith('.txt'):
                try:
                    # Use enscript to convert text to properly formatted PostScript
                    ps_file = tempfile.NamedTemporaryFile(suffix='.ps', delete=False)
                    ps_file.close()
                    
                    enscript_cmd = [
                        'enscript', 
                        '--font=Courier10',  # 10pt Courier font
                        '--margins=72:72:72:72',  # 1 inch margins
                        '--output=' + ps_file.name,
                        '--quiet',
                        file_path
                    ]
                    
                    result = subprocess.run(enscript_cmd, capture_output=True, text=True, timeout=15)
                    
                    if result.returncode == 0 and os.path.exists(ps_file.name):
                        # Print the PostScript file using lpr
                        lpr_cmd = ['lpr', '-H', f'{host}:{port}', ps_file.name]
                        
                        if copies > 1:
                            lpr_cmd.extend(['-#', str(copies)])
                            
                        lpr_result = subprocess.run(lpr_cmd, capture_output=True, text=True, timeout=30)
                        
                        # Clean up
                        os.unlink(ps_file.name)
                        
                        if lpr_result.returncode == 0:
                            print(f"Print job sent successfully via enscript -> PostScript -> lpr")
                            return True
                        else:
                            print(f"lpr failed after enscript: {lpr_result.stderr}")
                    else:
                        print(f"enscript failed: {result.stderr}")
                        os.unlink(ps_file.name)
                        
                except (FileNotFoundError, subprocess.SubprocessError, subprocess.TimeoutExpired):
                    pass
            
            # Method 2: Convert to PostScript for text files and use lpr
            if file_path.endswith('.txt'):
                try:
                    ps_file = self._convert_text_to_postscript(file_path)
                    if ps_file:
                        # Try to print PostScript directly via lpr
                        cmd = ['lpr', '-H', f'{host}:{port}', ps_file]
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                        
                        # Clean up temp file
                        os.unlink(ps_file)
                        
                        if result.returncode == 0:
                            print(f"Print job sent successfully via PostScript")
                            return True
                        else:
                            print(f"PostScript lpr failed: {result.stderr}")
                            
                except (FileNotFoundError, subprocess.SubprocessError):
                    pass
            
            # Method 3: Use CUPS lp command directly to IP
            try:
                cmd = ['lp', '-h', f'{host}:{port}', '-d', 'ipp']
                
                if copies > 1:
                    cmd.extend(['-n', str(copies)])
                    
                lp_options = []
                if duplex:
                    lp_options.append('sides=two-sided-long-edge')
                    
                if lp_options:
                    cmd.extend(['-o', ','.join(lp_options)])
                    
                cmd.append(file_path)
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print(f"Print job sent successfully via lp command")
                    return True
                else:
                    print(f"lp command failed: {result.stderr}")
                    
            except (FileNotFoundError, subprocess.SubprocessError):
                pass
                
            # Method 4: For Canon printers, try PCL format for text
            if file_path.endswith('.txt'):
                try:
                    pcl_data = self._convert_text_to_pcl(file_path)
                    if pcl_data:
                        # Send PCL data to port 9100
                        cmd = ['nc', '-w', '10', host, '9100']
                        result = subprocess.run(cmd, input=pcl_data, text=False,
                                              capture_output=True, timeout=30)
                        
                        if result.returncode == 0:
                            print(f"Print job sent successfully via PCL to port 9100")
                            return True
                        else:
                            print(f"PCL netcat failed: {result.stderr.decode()}")
                            
                except (FileNotFoundError, subprocess.SubprocessError):
                    pass
                    
        except Exception as e:
            print(f"IPP printing failed: {e}")
            
        return False
            
    def _alternative_print_method(self, file_path: str, printer_uri: str, copies: int,
                                 duplex: bool, quality: str) -> bool:
        """Alternative printing method using cross-platform fallbacks"""
        try:
            # Try platform-specific file opening for printing
            success = self.platform.open_file_for_printing(file_path)
            if success:
                print("Opened file with system default application. Please print manually.")
                return True
            else:
                print("Could not open file for printing")
                return False
                
        except Exception as e:
            print(f"Alternative print method failed: {e}")
            return False
                
    def _extract_printer_name(self, printer_uri: str) -> Optional[str]:
        """Extract printer name from various URI formats"""
        try:
            parsed = urllib.parse.urlparse(printer_uri)
            
            # For IPP URIs, extract from path
            if parsed.scheme in ['ipp', 'ipps']:
                path_parts = parsed.path.strip('/').split('/')
                if path_parts and path_parts[0] != 'ipp':
                    return path_parts[0]
                    
            # For other schemes, try to extract from hostname or path
            if parsed.hostname:
                return parsed.hostname
                
        except Exception:
            pass
            
        return None
        
    def _convert_text_to_postscript(self, file_path: str) -> Optional[str]:
        """Convert text file to PostScript format"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Create PostScript document
            ps_content = f"""%!PS-Adobe-3.0
%%Creator: Canon Printer CLI
%%Title: {os.path.basename(file_path)}
%%Pages: 1
%%BoundingBox: 0 0 612 792
%%EndComments

/Courier findfont 10 scalefont setfont

%%Page: 1 1
72 720 moveto
"""
            
            # Split content into lines and add PostScript commands
            lines = content.split('\n')
            y_position = 720
            
            for line in lines:
                # Escape special PostScript characters
                escaped_line = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
                ps_content += f"({escaped_line}) show\n"
                y_position -= 12  # Move down for next line
                ps_content += f"72 {y_position} moveto\n"
                
                if y_position < 72:  # Start new page if needed
                    ps_content += "showpage\n%%Page: 2 2\n72 720 moveto\n"
                    y_position = 720
                    
            ps_content += "\nshowpage\n%%EOF\n"
            
            # Write to temporary file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.ps', delete=False)
            temp_file.write(ps_content)
            temp_file.close()
            
            return temp_file.name
            
        except Exception as e:
            print(f"Error converting to PostScript: {e}")
            return None
            
    def _convert_text_to_pcl(self, file_path: str) -> Optional[bytes]:
        """Convert text file to PCL (Printer Command Language) format"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # PCL commands for text printing
            pcl_data = bytearray()
            
            # PCL Reset
            pcl_data.extend(b'\x1b\x45')  # ESC E (reset)
            
            # Set font (Courier 12pt)
            pcl_data.extend(b'\x1b\x28\x73\x31\x32\x48')  # ESC(s12H (pitch)
            pcl_data.extend(b'\x1b\x28\x73\x30\x53')     # ESC(s0S (style - upright)
            pcl_data.extend(b'\x1b\x28\x73\x30\x42')     # ESC(s0B (stroke weight - medium)
            pcl_data.extend(b'\x1b\x28\x73\x33\x54')     # ESC(s3T (typeface - Courier)
            
            # Set top margin
            pcl_data.extend(b'\x1b\x26\x6c\x36\x45')     # ESC&l6E (top margin 6 lines)
            
            # Add the text content
            pcl_data.extend(content.encode('utf-8'))
            
            # Form feed to eject page
            pcl_data.extend(b'\x0c')
            
            # PCL Reset
            pcl_data.extend(b'\x1b\x45')  # ESC E (reset)
            
            return bytes(pcl_data)
            
        except Exception as e:
            print(f"Error converting to PCL: {e}")
            return None
        
    def _get_mime_by_extension(self, extension: str) -> Optional[str]:
        """Get MIME type by file extension"""
        extension_map = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.ps': 'application/postscript',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }
        
        return extension_map.get(extension.lower())
        
    def get_supported_formats(self) -> list:
        """Get list of supported file formats"""
        return list(self.supported_formats.keys())
        
    def is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported"""
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            ext = Path(file_path).suffix.lower()
            mime_type = self._get_mime_by_extension(ext)
            
        return mime_type in self.supported_formats
        
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get information about a file"""
        if not os.path.exists(file_path):
            return {}
            
        stat = os.stat(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        
        if not mime_type:
            ext = Path(file_path).suffix.lower()
            mime_type = self._get_mime_by_extension(ext)
            
        return {
            'path': file_path,
            'name': os.path.basename(file_path),
            'size': stat.st_size,
            'mime_type': mime_type,
            'supported': self.is_supported_format(file_path),
            'extension': Path(file_path).suffix.lower()
        }
        
    def cleanup_temp_files(self):
        """Clean up any temporary files created during processing"""
        # This would be called to clean up temporary files
        # For now, we'll rely on the OS to clean up temp files
        pass
