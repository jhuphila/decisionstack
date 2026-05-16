#!/bin/bash

echo ""
echo "=================================="
echo "  DecisionStack — Setup Script"
echo "=================================="
echo ""

# --- Check Python version ---
echo "Checking Python version..."
python_version=$(python3 --version 2>&1)
if [ $? -ne 0 ]; then
    echo "❌ Python 3 not found. Please install Python 3.10+ from python.org"
    exit 1
fi
echo "✅ Found $python_version"
echo ""

# --- Create virtual environment ---
echo "Creating virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "❌ Failed to create virtual environment."
    exit 1
fi
echo "✅ Virtual environment created"
echo ""

# --- Activate and install dependencies ---
echo "Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies. Check requirements.txt"
    exit 1
fi
echo "✅ Dependencies installed"
echo ""

# --- Create .env if it doesn't exist ---
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
else
    echo "✅ .env file already exists — skipping"
    echo ""
fi

# --- Check ngrok ---
echo "Checking for ngrok..."
if command -v ngrok &> /dev/null; then
    echo "✅ ngrok is already installed"
else
    echo "⚠️  ngrok not found."
    echo ""
    echo "   Please install ngrok manually:"
    echo "   1. Go to https://ngrok.com/download"
    echo "   2. Create a free account and download ngrok for your OS"
    echo "   3. Run: ngrok config add-authtoken YOUR_TOKEN_HERE"
    echo "      (get your token from https://dashboard.ngrok.com)"
fi
echo ""

# --- Done ---
echo "=================================="
echo "  Setup complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo ""
echo "  1. Open .env and fill in your credentials:"
echo "       DISCORD_TOKEN"
echo "       ANTHROPIC_API_KEY"
echo "       AIRTABLE_API_KEY"
echo "       AIRTABLE_BASE_ID"
echo "       DISCORD_GUILD_ID"
echo ""
echo "  2. Activate your virtual environment:"
echo "       source venv/bin/activate"
echo ""
echo "  3. Run the bot:"
echo "       python main.py"
echo ""
echo "  4. In a separate terminal, start ngrok:"
echo "       ngrok http 5000"
echo ""
echo "  See README.md for full setup instructions."
echo ""
