# Canon Printer CLI

A cross-platform command-line tool for printing documents to Canon printers via IPP (Internet Printing Protocol). Works on Windows, macOS, and Linux.

## Features

- 🖨️ **Cross-platform printing** - Works on Windows, macOS, and Linux
- 🔍 **Auto-discovery** - Automatically finds Canon printers on your network
- 📄 **Multiple file formats** - Supports PDF, images, text files, and Office documents
- ⚙️ **Flexible options** - Control copies, duplex printing, and quality settings
- 💾 **Configuration management** - Save printer preferences and settings
- 🌐 **Network printing** - Print to network printers via IPP
- 📊 **Printer management** - List, test, and manage your Canon printers

## Supported File Types

- **Documents**: PDF, TXT, PostScript
- **Images**: JPEG, PNG, GIF, TIFF
- **Office**: DOC, DOCX, XLS, XLSX (requires LibreOffice on Unix systems)

## Installation

### Prerequisites

#### All Platforms
- Python 3.7 or higher
- Canon printer with network connectivity or USB connection
- Canon printer drivers installed

#### Windows
- No additional system packages required
- Uses Windows Print Spooler service

#### macOS/Linux
- CUPS printing system
- LibreOffice (optional, for Office document conversion)

```bash
# macOS (using Homebrew)
brew install cups

# Ubuntu/Debian
sudo apt install cups cups-client libreoffice

# CentOS/RHEL/Fedora
sudo yum install cups cups-client libreoffice
# or
sudo dnf install cups cups-client libreoffice
```

### Install from PyPI (when published)

```bash
pip install canon-printer-cli
```

### Install from Source

```bash
# Clone the repository
git clone https://github.com/your-username/canon-printer-cli.git
cd canon-printer-cli

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## Quick Start

### 1. Discover Printers

```bash
python main.py discover
```

### 2. Print a Document

```bash
# Print with default settings
python main.py print document.pdf

# Print with custom options
python main.py print photo.jpg -c 2 --quality high --duplex
```

### 3. List All Printers

```bash
python main.py list
```

### 4. Print a Test Page

```bash
python main.py test
```

## Usage

### Command Line Interface

```bash
python main.py <command> [options]
```

#### Available Commands

| Command | Description |
|---------|-------------|
| `print <file>` | Print a document |
| `discover` | Discover Canon printers on network |
| `list` | List all discovered printers with details |
| `test` | Print a test page |

#### Print Options

| Option | Description | Default |
|--------|-------------|---------|
| `-p, --printer URI` | Specific printer URI | Auto-discover |
| `-c, --copies N` | Number of copies | 1 |
| `-d, --duplex` | Print double-sided | False |
| `-q, --quality LEVEL` | Print quality (draft/normal/high) | normal |

### Examples

```bash
# Basic printing
python main.py print document.pdf

# Print multiple copies in high quality
python main.py print report.pdf -c 3 --quality high

# Print double-sided
python main.py print presentation.pdf --duplex

# Print to specific printer
python main.py print photo.jpg -p "ipp://192.168.1.100:631/ipp/print"

# Print test page to specific printer
python main.py test -p "Canon PIXMA MG3620"
```

## Configuration

The tool creates a configuration directory at:
- **Windows**: `%USERPROFILE%\.canon-printer-cli`
- **macOS/Linux**: `~/.canon-printer-cli`

### Configuration Files

- `config.yaml` - Main configuration settings
- `printers.json` - Cached printer information and preferences

### Default Settings

```yaml
default_printer: null
default_copies: 1
default_duplex: false
default_quality: normal
auto_discover: true
save_printer_history: true
preferred_paper_size: A4
network:
  scan_ranges:
    - 192.168.1.0/24
    - 192.168.0.0/24
    - 10.0.0.0/24
  ports: [631, 9100, 8080, 80]
  max_workers: 50
```

## Platform-Specific Notes

### Windows

- Uses Windows Print Spooler API via WMI and win32print
- Supports both network and local USB printers
- Falls back to PowerShell commands if Python bindings unavailable
- Can open files with default applications for printing

### macOS

- Uses CUPS printing system via `lpr` and `lpstat` commands
- Supports Bonjour/mDNS printer discovery
- Can use Preview app as fallback for manual printing
- Supports both network and USB printers

### Linux

- Uses CUPS printing system
- Requires `cups` and `cups-client` packages
- LibreOffice recommended for Office document conversion
- Supports IPP and network printer discovery

## Troubleshooting

### Common Issues

1. **No printers found**
   - Ensure Canon printer is powered on and connected to network
   - Check that printer drivers are installed
   - Verify printer supports IPP (most modern Canon printers do)
   - Try specifying printer IP manually: `python main.py print file.pdf -p ipp://192.168.1.100:631`

2. **Print job fails**
   - Check printer status and paper/ink levels
   - Verify file format is supported
   - Try printing a test page first: `python main.py test`
   - Use system default application as fallback

3. **Permission errors (Linux/macOS)**
   - Add user to `lp` group: `sudo usermod -a -G lp $USER`
   - Restart session after group change

4. **Office document conversion fails**
   - Install LibreOffice: `sudo apt install libreoffice` (Ubuntu/Debian)
   - Ensure LibreOffice is in system PATH
   - Try converting manually first: `libreoffice --headless --convert-to pdf document.docx`

### Debug Mode

Enable verbose logging by modifying the configuration:

```yaml
logging:
  enabled: true
  level: DEBUG
  file: ~/.canon-printer-cli/debug.log
```

### Network Discovery Issues

If auto-discovery doesn't work:

1. **Check network configuration**
   ```bash
   # Test printer connectivity
   ping 192.168.1.100  # Replace with printer IP
   telnet 192.168.1.100 631  # Test IPP port
   ```

2. **Manual printer addition**
   - Find printer IP from printer's network settings menu
   - Use full IPP URI: `ipp://PRINTER_IP:631/ipp/print`

3. **Firewall issues**
   - Ensure ports 631, 9100, 8080, and 80 are not blocked
   - Temporarily disable firewall to test

## Development

### Setting up Development Environment

```bash
# Clone repository
git clone https://github.com/your-username/canon-printer-cli.git
cd canon-printer-cli

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install -e .[dev]
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=canon_printer_cli

# Run specific test file
pytest tests/test_printer_discovery.py
```

### Code Formatting

```bash
# Format code
black .

# Check linting
flake8

# Type checking
mypy .
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `pytest`
5. Format code: `black .`
6. Commit changes: `git commit -am 'Add feature'`
7. Push to branch: `git push origin feature-name`
8. Submit a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Canon for creating reliable printers with IPP support
- CUPS project for excellent Unix printing infrastructure
- Python community for excellent cross-platform libraries

## Support

- 📖 [Documentation](README.md)
- 🐛 [Issue Tracker](https://github.com/your-username/canon-printer-cli/issues)
- 💬 [Discussions](https://github.com/your-username/canon-printer-cli/discussions)

---

**Note**: This tool is not officially affiliated with Canon Inc. Canon is a trademark of Canon Inc.
