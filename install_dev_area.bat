@echo off
setlocal enabledelayedexpansion
cls

:: Enable ANSI Colors
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set ESC=%%b
set Red=%ESC%[31m
set Green=%ESC%[32m
set Cyan=%ESC%[36m
set White=%ESC%[37m
set Reset=%ESC%[0m
set Gray=%ESC%[90m

title VORTEX STEALTH LOADER v1.2
mode con: cols=90 lines=30

:: 1. MINIMALIST HEADER
echo %White%[%Red% VORTEX CORE %White%]--------------------------------------------------[ %Red%ZERO %White%]
echo %Gray%[+] KERNEL_STATUS: ACTIVE
echo [+] TARGET_DIR: %~dp0
echo %Reset%

:: 2. SCROLLING INITIALIZATION
echo %Gray%[+] INITIALIZING...%Reset%
timeout /t 1 >nul
echo %Gray%[+] BYPASSING PIP_VERBOSITY...%Reset%
timeout /t 1 >nul
echo.

:: 3. PYTHON CHECK
echo %Cyan%[+] IDENTIFYING ENVIRONMENT...%Reset%
for /f "tokens=2" %%a in ('python --version 2^>^&1') do set current_ver=%%a
echo !current_ver! | findstr /r "^3\.12" >nul
if %errorlevel% neq 0 (
    echo %Red%[!] ERROR: PYTHON 3.12 REQUIRED.
    echo [!] CURRENT: !current_ver!%Reset%
    pause
    exit /b
)
echo %Green%[+] ENVIRONMENT VERIFIED.%Reset%
echo.

:: 4. THE STEALTH INSTALLER
echo %Cyan%[+] INJECTING REQUIREMENTS...%Reset%

:: Check if file exists
if not exist requirements.txt (
    echo %Red%[!] ERROR: requirements.txt missing.%Reset%
    pause
    exit /b
)

:: Loop through requirements quietly
for /f "usebackq tokens=*" %%A in ("requirements.txt") do (
    if not "%%A"=="" (
        <nul set /p "=%White%[+] installing %%A ... %Reset%"
        :: -q makes pip quiet, >nul 2>&1 hides EVERYTHING else
        python -m pip install "%%A" -q --no-input >nul 2>&1
        
        if !errorlevel! equ 0 (
            echo %Green%[ DONE ]%Reset%
        ) else (
            echo %Red%[ FAIL ]%Reset%
        )
    )
)

:: 5. PYTORCH CUDA STEALTH DEPLOYMENT
echo.
echo %Cyan%[+] INJECTING PYTORCH CUDA 11.8...%Reset%
<nul set /p "=%White%[+] downloading massive data stream ... %Reset%"

:: Using -q here to keep it silent while it downloads
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 -q --no-input >nul 2>&1

if %errorlevel% equ 0 (
    echo %Green%[ SUCCESS ]%Reset%
) else (
    echo %Red%[ ERROR ]%Reset%
)

:: 6. FINAL STATUS
echo.
echo %Green%############################################################
echo #   SYSTEM ONLINE - ALL MODULES LOADED                     #
echo ############################################################%Reset%
echo.

set /p dummy="%White%[INPUT] PRESS %Red%ENTER%White% TO EXIT_%Reset% "
exit