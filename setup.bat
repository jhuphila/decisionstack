@echo off
echo.
echo ==================================
echo   DecisionStack -- Setup Script
echo ==================================
echo.

:: --- Check Python ---
echo Checking Python version...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo X Python not found. Please install Python 3.10+ from python.org
    echo   Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo Found %%i
echo.

:: --- Create virtual environment ---
echo Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo X Failed to create virtual environment.
    pause
    exit /b 1
)
echo [OK] Virtual environment created
echo.

:: --- Activate and install dependencies ---
echo Installing dependencies...
call venv\Scripts\activate
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo X Failed to install dependencies. Check requirements.txt
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

:: --- Create .env if it doesn't exist ---
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env >nul
    echo [OK] .env file created
) else (
    echo [OK] .env file already exists -- skipping
)
echo.

:: --- Check ngrok ---
echo Checking for ngrok...
where ngrok >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] ngrok is already installed
) else (
    echo [!] ngrok not found.
    echo.
    echo     Please install ngrok manually:
    echo     1. Go to https://ngrok.com/download
    echo     2. Create a free account and download ngrok for Windows
    echo     3. Extract ngrok.exe somewhere easy like C:\ngrok\
    echo     4. Add that folder to your PATH, or run ngrok from that folder
    echo     5. Run: ngrok config add-authtoken YOUR_TOKEN_HERE
    echo        ^(get your token from https://dashboard.ngrok.com^)
)
echo.

:: --- Done ---
echo ==================================
echo   Setup complete!
echo ==================================
echo.
echo Next steps:
echo.
echo   1. Open .env in any text editor and fill in your credentials:
echo        DISCORD_TOKEN
echo        ANTHROPIC_API_KEY
echo        AIRTABLE_API_KEY
echo        AIRTABLE_BASE_ID
echo        DISCORD_GUILD_ID
echo.
echo   2. Activate your virtual environment:
echo        venv\Scripts\activate
echo.
echo   3. Run the bot:
echo        python main.py
echo.
echo   4. In a separate terminal, start ngrok:
echo        ngrok http 5000
echo.
echo   See README.md for full setup instructions.
echo.
pause
