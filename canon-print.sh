#!/bin/bash

# Canon Printer CLI - Unix Shell Script with Auto Python Installation
# Supports macOS (Intel/Apple Silicon) and Linux (x64/ARM64)

set -e

echo "Canon Printer CLI - Unix Launcher"
echo "================================="

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Detect OS and architecture
echo "Detecting system..."
OS=$(uname -s)
ARCH=$(uname -m)

case "$OS" in
    Darwin*)
        OS_NAME="macOS"
        if [[ "$ARCH" == "arm64" ]]; then
            ARCH_DISPLAY="Apple Silicon (M1/M2/M3)"
            PYTHON_ARCH="arm64"
        else
            ARCH_DISPLAY="Intel"
            PYTHON_ARCH="x64"
        fi
        ;;
    Linux*)
        OS_NAME="Linux"
        if [[ "$ARCH" == "x86_64" ]]; then
            ARCH_DISPLAY="x64"
            PYTHON_ARCH="x64"
        elif [[ "$ARCH" == "aarch64" ]] || [[ "$ARCH" == "arm64" ]]; then
            ARCH_DISPLAY="ARM64"
            PYTHON_ARCH="arm64"
        elif [[ "$ARCH" == "armv7l" ]]; then
            ARCH_DISPLAY="ARMv7"
            PYTHON_ARCH="armv7"
        else
            ARCH_DISPLAY="$ARCH"
            PYTHON_ARCH="$ARCH"
        fi
        ;;
    *)
        echo "Warning: Unsupported OS: $OS"
        OS_NAME="$OS"
        ARCH_DISPLAY="$ARCH"
        PYTHON_ARCH="$ARCH"
        ;;
esac

echo "Detected: $OS_NAME on $ARCH_DISPLAY"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Python on macOS
install_python_macos() {
    echo "Installing Python on macOS..."
    
    # Check if Homebrew is available
    if command_exists brew; then
        echo "Using Homebrew to install Python..."
        brew install python@3.11
        
        # Create symlinks if needed
        if ! command_exists python && command_exists python3; then
            echo "Creating python symlink..."
            # Try to add to PATH or create local symlink
            mkdir -p "$HOME/.local/bin"
            ln -sf "$(which python3)" "$HOME/.local/bin/python"
            export PATH="$HOME/.local/bin:$PATH"
        fi
        return 0
    fi
    
    # Check if MacPorts is available
    if command_exists port; then
        echo "Using MacPorts to install Python..."
        sudo port install python311
        sudo port select --set python python311
        return 0
    fi
    
    # Download and install Python manually
    echo "No package manager found. Downloading Python installer..."
    
    PYTHON_VERSION="3.11.7"
    if [[ "$PYTHON_ARCH" == "arm64" ]]; then
        PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-macos11.pkg"
    else
        PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-macosx10.9.pkg"
    fi
    
    TEMP_DIR=$(mktemp -d)
    INSTALLER_PATH="$TEMP_DIR/python-installer.pkg"
    
    echo "Downloading from: $PYTHON_URL"
    if command_exists curl; then
        curl -L -o "$INSTALLER_PATH" "$PYTHON_URL"
    elif command_exists wget; then
        wget -O "$INSTALLER_PATH" "$PYTHON_URL"
    else
        echo "Error: Neither curl nor wget found. Cannot download Python."
        return 1
    fi
    
    if [[ ! -f "$INSTALLER_PATH" ]]; then
        echo "Error: Failed to download Python installer"
        return 1
    fi
    
    echo "Installing Python (requires admin password)..."
    sudo installer -pkg "$INSTALLER_PATH" -target /
    
    # Clean up
    rm -rf "$TEMP_DIR"
    
    # Update PATH
    export PATH="/usr/local/bin:/Library/Frameworks/Python.framework/Versions/3.11/bin:$PATH"
    
    return 0
}

# Function to install Python on Linux
install_python_linux() {
    echo "Installing Python on Linux..."
    
    # Detect Linux distribution
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        DISTRO=$ID
    else
        DISTRO="unknown"
    fi
    
    case "$DISTRO" in
        ubuntu|debian)
            echo "Detected Debian/Ubuntu. Installing Python via apt..."
            sudo apt update
            sudo apt install -y python3 python3-pip python3-venv python3-dev
            
            # Create python symlink if needed
            if ! command_exists python && command_exists python3; then
                sudo apt install -y python-is-python3 2>/dev/null || {
                    echo "Creating python symlink..."
                    sudo ln -sf /usr/bin/python3 /usr/local/bin/python
                }
            fi
            ;;
            
        fedora|centos|rhel)
            echo "Detected RedHat/Fedora. Installing Python via dnf/yum..."
            if command_exists dnf; then
                sudo dnf install -y python3 python3-pip python3-venv python3-devel
            else
                sudo yum install -y python3 python3-pip python3-venv python3-devel
            fi
            
            # Create python symlink if needed
            if ! command_exists python && command_exists python3; then
                sudo ln -sf /usr/bin/python3 /usr/local/bin/python
            fi
            ;;
            
        arch)
            echo "Detected Arch Linux. Installing Python via pacman..."
            sudo pacman -S --noconfirm python python-pip
            ;;
            
        opensuse*)
            echo "Detected openSUSE. Installing Python via zypper..."
            sudo zypper install -y python3 python3-pip python3-venv python3-devel
            
            if ! command_exists python && command_exists python3; then
                sudo ln -sf /usr/bin/python3 /usr/local/bin/python
            fi
            ;;
            
        *)
            echo "Unsupported Linux distribution: $DISTRO"
            echo "Please install Python 3.7+ manually using your system's package manager"
            echo "Common commands:"
            echo "  apt install python3 python3-pip        # Debian/Ubuntu"
            echo "  dnf install python3 python3-pip        # Fedora"
            echo "  yum install python3 python3-pip        # CentOS/RHEL"
            echo "  pacman -S python python-pip             # Arch"
            echo "  zypper install python3 python3-pip     # openSUSE"
            return 1
            ;;
    esac
    
    return 0
}

# Check if Python is available
echo "Checking Python installation..."
if command_exists python; then
    PYTHON_CMD="python"
elif command_exists python3; then
    PYTHON_CMD="python3"
    # Create a local alias for this session
    alias python=python3
else
    echo "Python is not installed or not in PATH"
    
    read -p "Would you like to install Python automatically? (Y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        case "$OS_NAME" in
            macOS)
                if ! install_python_macos; then
                    echo "Failed to install Python automatically."
                    echo "Please install Python manually from https://python.org"
                    echo "or use a package manager like Homebrew: brew install python"
                    exit 1
                fi
                ;;
            Linux)
                if ! install_python_linux; then
                    echo "Failed to install Python automatically."
                    exit 1
                fi
                ;;
            *)
                echo "Automatic installation not supported for $OS_NAME"
                echo "Please install Python manually from https://python.org"
                exit 1
                ;;
        esac
        
        # Verify installation
        if command_exists python; then
            PYTHON_CMD="python"
        elif command_exists python3; then
            PYTHON_CMD="python3"
            alias python=python3
        else
            echo "Python installation may have failed. Please restart your terminal and try again."
            exit 1
        fi
    else
        echo "Please install Python manually and run this script again."
        exit 1
    fi
fi

# Get Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
echo "Found Python $PYTHON_VERSION"

# Check Python version (require 3.7+)
PYTHON_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.minor)")

if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 7 ]]; then
    echo "Error: Python 3.7 or higher is required (found $PYTHON_VERSION)"
    echo "Please upgrade Python or install a newer version"
    exit 1
fi

# Check for pip
echo "Checking for pip..."
if ! $PYTHON_CMD -m pip --version >/dev/null 2>&1; then
    echo "pip is not available. Attempting to install..."
    
    case "$OS_NAME" in
        macOS)
            if command_exists brew; then
                brew install python@3.11
            else
                $PYTHON_CMD -m ensurepip --default-pip
            fi
            ;;
        Linux)
            echo "Please install pip using your system package manager:"
            echo "  apt install python3-pip        # Debian/Ubuntu"
            echo "  dnf install python3-pip        # Fedora"
            echo "  yum install python3-pip        # CentOS/RHEL"
            exit 1
            ;;
    esac
fi

# Check dependencies
echo "Checking Python dependencies..."

# Create requirements.txt if it doesn't exist
if [[ ! -f "requirements.txt" ]]; then
    echo "Warning: requirements.txt not found. Creating minimal requirements..."
    cat > requirements.txt << EOF
requests>=2.28.0
PyYAML>=6.0
Pillow>=9.0.0
zeroconf>=0.39.0
python-cups>=1.9.73; sys_platform == "linux"
EOF
fi

# Check if required packages are installed
if ! $PYTHON_CMD -c "import requests, yaml, PIL" >/dev/null 2>&1; then
    echo "Installing required Python packages..."
    
    # Install system dependencies for certain packages
    case "$OS_NAME" in
        Linux)
            echo "Installing system dependencies..."
            case "$DISTRO" in
                ubuntu|debian)
                    sudo apt install -y python3-dev libjpeg-dev libpng-dev libavahi-client-dev libcups2-dev
                    ;;
                fedora|centos|rhel)
                    if command_exists dnf; then
                        sudo dnf install -y python3-devel libjpeg-devel libpng-devel avahi-devel cups-devel
                    else
                        sudo yum install -y python3-devel libjpeg-devel libpng-devel avahi-devel cups-devel
                    fi
                    ;;
            esac
            ;;
    esac
    
    $PYTHON_CMD -m pip install --upgrade pip
    $PYTHON_CMD -m pip install -r requirements.txt
    
    if [[ $? -ne 0 ]]; then
        echo "Warning: Failed to install some dependencies."
        echo "You may need to install them manually:"
        echo "  pip install requests PyYAML Pillow zeroconf python-cups"
        echo ""
        echo "Some functionality may be limited without all dependencies."
    fi
fi

# Check if main.py exists
if [[ ! -f "main.py" ]]; then
    echo "Error: main.py not found in $SCRIPT_DIR"
    echo "Please ensure you're running this script from the canon-printer-cli directory"
    exit 1
fi

# Install additional system dependencies
echo "Checking system dependencies..."
case "$OS_NAME" in
    macOS)
        # CUPS should be available by default on macOS
        if ! command_exists lpr; then
            echo "Warning: CUPS printing system not found"
        fi
        ;;
    Linux)
        if ! command_exists lpr; then
            echo "Installing CUPS printing system..."
            case "$DISTRO" in
                ubuntu|debian)
                    sudo apt install -y cups cups-client
                    ;;
                fedora|centos|rhel)
                    if command_exists dnf; then
                        sudo dnf install -y cups cups-client
                    else
                        sudo yum install -y cups cups-client
                    fi
                    ;;
                arch)
                    sudo pacman -S --noconfirm cups
                    ;;
                opensuse*)
                    sudo zypper install -y cups cups-client
                    ;;
            esac
            
            # Start CUPS service
            sudo systemctl enable cups
            sudo systemctl start cups
        fi
        ;;
esac

# Make the script executable
chmod +x "$0"

echo ""

# Show usage if no arguments provided
if [[ $# -eq 0 ]]; then
    echo "Usage Examples:"
    echo "  $0 discover                      - Find Canon printers"
    echo "  $0 add 192.168.1.100            - Add printer by IP address"
    echo "  $0 add 192.168.1.100 --name \"My Printer\" --test"
    echo "  $0 list                         - List all printers"
    echo "  $0 test                         - Print test page"
    echo "  $0 print document.pdf           - Print a document"
    echo ""
    echo "For more help: $0 [command] --help"
    echo ""
    echo "System Info:"
    echo "  OS: $OS_NAME on $ARCH_DISPLAY"
    echo "  Python: $PYTHON_VERSION"
    echo ""
fi

# Run the Python script with all arguments
$PYTHON_CMD main.py "$@"
EXIT_CODE=$?

# Show pause equivalent behavior for errors
if [[ $EXIT_CODE -ne 0 ]]; then
    echo ""
    echo "Command completed with error code: $EXIT_CODE"
    if [[ $# -eq 0 ]]; then
        read -p "Press Enter to continue..."
    fi
fi

exit $EXIT_CODE
