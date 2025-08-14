@echo off
REM Canon Printer CLI - Windows Batch Script with Auto Python Installation
REM Supports both x64 and ARM64 architectures

setlocal enabledelayedexpansion

echo Canon Printer CLI - Windows Launcher
echo ====================================

REM Get the directory where this batch file is located
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Detect system architecture
echo Detecting system architecture...
set ARCH=unknown
if defined PROCESSOR_ARCHITEW6432 (
    set ARCH=%PROCESSOR_ARCHITEW6432%
) else (
    set ARCH=%PROCESSOR_ARCHITECTURE%
)

REM Map architecture to Python installer type
if /i "%ARCH%"=="AMD64" (
    set PYTHON_ARCH=amd64
    set ARCH_DISPLAY=x64
) else if /i "%ARCH%"=="ARM64" (
    set PYTHON_ARCH=arm64
    set ARCH_DISPLAY=ARM64
) else if /i "%ARCH%"=="x86" (
    set PYTHON_ARCH=win32
    set ARCH_DISPLAY=x86 ^(32-bit^)
) else (
    echo Warning: Unknown architecture %ARCH%, defaulting to x64
    set PYTHON_ARCH=amd64
    set ARCH_DISPLAY=x64 ^(default^)
)

echo Detected architecture: %ARCH_DISPLAY%

REM Check if Python is available
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    goto :install_python
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo Found Python !PYTHON_VERSION!
    
    REM Check if it's 32-bit Python on 64-bit system (suboptimal)
    if /i "%ARCH%"=="AMD64" (
        python -c "import platform; exit(0 if platform.machine().endswith('64') else 1)" >nul 2>&1
        if errorlevel 1 (
            echo Warning: You have 32-bit Python on a 64-bit system
            echo Consider upgrading to 64-bit Python for better performance
        )
    )
    goto :check_dependencies
)

:install_python
echo.
echo Python is required but not installed.
set /p INSTALL_PYTHON="Would you like to install Python automatically? (Y/N): "
if /i "!INSTALL_PYTHON!"=="Y" (
    echo Installing Python for %ARCH_DISPLAY%...
    goto :download_python
) else (
    echo Please install Python manually from https://python.org
    echo Make sure to download the %ARCH_DISPLAY% version
    echo Check "Add Python to PATH" during installation
    pause
    exit /b 1
)

:download_python
echo.
echo Downloading Python installer for %ARCH_DISPLAY%...

REM Create temp directory
if not exist "%TEMP%\canon-printer-cli" mkdir "%TEMP%\canon-printer-cli"
set PYTHON_INSTALLER=%TEMP%\canon-printer-cli\python-installer.exe

REM Set Python download URL based on architecture
set PYTHON_VERSION=3.11.7
if /i "%PYTHON_ARCH%"=="amd64" (
    set PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-amd64.exe
) else if /i "%PYTHON_ARCH%"=="arm64" (
    set PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-arm64.exe
) else if /i "%PYTHON_ARCH%"=="win32" (
    set PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%.exe
) else (
    echo Error: Unsupported architecture for automatic installation
    echo Please install Python manually from https://python.org
    pause
    exit /b 1
)

echo Downloading from: %PYTHON_URL%
echo Please wait while downloading Python %PYTHON_VERSION% for %ARCH_DISPLAY%...

REM Download Python installer using PowerShell with better error handling
powershell -Command "& {
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $ProgressPreference = 'SilentlyContinue'
        Write-Host 'Starting download...'
        Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%' -UseBasicParsing
        Write-Host 'Download completed successfully'
        exit 0
    } catch {
        Write-Host 'Download failed:' $_.Exception.Message
        exit 1
    }
}"

if errorlevel 1 (
    echo Failed to download Python installer.
    echo.
    echo Please try one of these alternatives:
    echo 1. Check your internet connection and try again
    echo 2. Download Python manually from https://python.org
    echo    - Choose Python %PYTHON_VERSION% or later
    echo    - Select the %ARCH_DISPLAY% version
    echo    - Make sure to check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

if not exist "%PYTHON_INSTALLER%" (
    echo Installer file not found after download.
    echo Please install Python manually from https://python.org
    pause
    exit /b 1
)

echo Installing Python %PYTHON_VERSION% for %ARCH_DISPLAY%...
echo This may take a few minutes...
echo.
echo Installation options:
echo - Installing for all users
echo - Adding Python to PATH
echo - Including pip package manager

REM Install Python with comprehensive options
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_doc=0 Include_dev=0 Include_launcher=1 InstallLauncherAllUsers=1

REM Wait for installation to complete
echo Waiting for installation to complete...
timeout /t 10 >nul

REM Clean up installer
del "%PYTHON_INSTALLER%" >nul 2>&1
rmdir "%TEMP%\canon-printer-cli" >nul 2>&1

REM Refresh environment variables
echo Refreshing environment variables...
call :refresh_env

REM Check if Python is now available
echo Verifying Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo Python installation completed but Python is not in PATH.
    echo This might happen if:
    echo 1. Installation failed silently
    echo 2. PATH variables haven't been refreshed
    echo.
    echo Please try one of these solutions:
    echo 1. Restart your command prompt and run this script again
    echo 2. Log out and log back in to Windows
    echo 3. Install Python manually from https://python.org
    echo.
    pause
    exit /b 1
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set NEW_PYTHON_VERSION=%%i
    echo Python !NEW_PYTHON_VERSION! installed successfully!
)

:check_dependencies
echo.
echo Checking Python dependencies...

REM Check if pip is available
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo Warning: pip is not available. Installing dependencies may fail.
)

REM Check if requirements.txt exists
if not exist "requirements.txt" (
    echo Warning: requirements.txt not found.
    echo Creating minimal requirements...
    (
        echo requests^>=2.28.0
        echo PyYAML^>=6.0
        echo Pillow^>=9.0.0
        echo zeroconf^>=0.39.0
    ) > requirements.txt
    
    REM Add platform-specific requirements
    if /i "%PYTHON_ARCH%"=="amd64" (
        echo pywin32^>=227; sys_platform == "win32" >> requirements.txt
        echo wmi^>=1.5.1; sys_platform == "win32" >> requirements.txt
    ) else if /i "%PYTHON_ARCH%"=="arm64" (
        echo # pywin32 and wmi may have limited ARM64 support >> requirements.txt
        echo pywin32^>=227; sys_platform == "win32" >> requirements.txt
        echo wmi^>=1.5.1; sys_platform == "win32" >> requirements.txt
    )
)

REM Check if required packages are installed
echo Checking for required packages...
python -c "import requests, yaml, PIL" >nul 2>&1
if errorlevel 1 (
    echo Installing required Python packages...
    python -m pip install --upgrade pip
    
    if /i "%PYTHON_ARCH%"=="arm64" (
        echo Note: Some packages may need to compile from source on ARM64
        echo This could take several minutes...
    )
    
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Warning: Failed to install some dependencies.
        echo You may need to install them manually or try:
        echo   pip install requests PyYAML Pillow zeroconf
        echo.
        if /i "%PYTHON_ARCH%"=="arm64" (
            echo Note for ARM64: Some packages may not have pre-built wheels
            echo and may require Visual Studio Build Tools to compile.
        )
        REM Continue anyway - some functionality may still work
    )
)

:run_script
echo.
REM Check if main.py exists
if not exist "main.py" (
    echo Error: main.py not found in %SCRIPT_DIR%
    echo Please ensure you're running this script from the canon-printer-cli directory
    pause
    exit /b 1
)

REM Show usage if no arguments provided
if "%~1"=="" (
    echo Usage Examples:
    echo   %~nx0 discover           - Find Canon printers
    echo   %~nx0 list              - List all printers  
    echo   %~nx0 test              - Print test page
    echo   %~nx0 print document.pdf - Print a document
    echo.
    echo For more help: %~nx0 print --help
    echo.
    echo System Info:
    echo   Architecture: %ARCH_DISPLAY%
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do echo   Python: %%i
    echo.
)

REM Run the Python script with all arguments
python main.py %*
set EXIT_CODE=!ERRORLEVEL!

REM Show pause only on error or if no arguments
if !EXIT_CODE! neq 0 (
    echo.
    echo Command completed with error code: !EXIT_CODE!
    pause
) else if "%~1"=="" (
    pause
)

exit /b !EXIT_CODE!

:refresh_env
REM Refresh environment variables without restarting
for /f "tokens=2*" %%a in ('reg query "HKLM\System\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SysPath=%%b"
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "UserPath=%%b"
if defined UserPath (
    set "PATH=%UserPath%;%SysPath%"
) else (
    set "PATH=%SysPath%"
)
REM Also try to refresh from registry for Python paths
for /f "tokens=2*" %%a in ('reg query "HKLM\System\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "PATH=!PATH!;%%b"
goto :eof
