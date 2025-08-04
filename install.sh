#!/bin/bash

# Kali Solana Trading Bot Installation Script

echo "🌙 Kali Trading Bot Installation Starting..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✅ Python $python_version detected (>= 3.9 required)"
else
    echo "❌ Python 3.9+ required. Current version: $python_version"
    exit 1
fi

# Check if we're in conda environment
if [[ "$CONDA_DEFAULT_ENV" ]]; then
    echo "✅ Conda environment detected: $CONDA_DEFAULT_ENV"
    use_conda=true
else
    echo "ℹ️  No conda environment detected. Using pip."
    use_conda=false
fi

# Install packages
echo "📦 Installing required packages..."

if [ "$use_conda" = true ]; then
    # Try conda first, fallback to pip
    conda install -c conda-forge pandas requests -y
    pip install -r requirements.txt
else
    pip install -r requirements.txt
fi

# Check if installation was successful
if [ $? -eq 0 ]; then
    echo "✅ All packages installed successfully!"
else
    echo "❌ Package installation failed. Please check errors above."
    exit 1
fi

# Create dontshare.py if it doesn't exist
if [ ! -f "dontshare.py" ]; then
    echo "📋 Creating dontshare.py from template..."
    cp dontshare.example.py dontshare.py
    echo "⚠️  Please update dontshare.py with your API keys!"
else
    echo "ℹ️  dontshare.py already exists"
fi

# Check data directory
if [ ! -d "data" ]; then
    echo "📁 Creating data directory..."
    mkdir data
fi

echo ""
echo "🎉 Installation Complete!"
echo ""
echo "Next steps:"
echo "1. Update dontshare.py with your API keys"
echo "2. Update MY_SOLANA_ADDERESS in config.py"
echo "3. Fund your wallet with SOL and USDC"
echo "4. Run: python main.py"
echo ""
echo "For VPS deployment: screen -S kali-bot python main.py"
echo "🌙 Happy trading!"