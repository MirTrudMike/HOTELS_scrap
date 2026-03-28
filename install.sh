#!/bin/bash
set -e

# ─────────────────────────────────────────────
#  Hotel Scraper — Installation Script
# ─────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║        Hotel Scraper — Installation          ║${NC}"
echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── Step 0: Check system requirements ────────────────────────────────────────

echo -e "${BOLD}Checking system requirements...${NC}"
echo ""

# Python 3
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}✗ Python 3 is not installed. Please install Python 3.10+${NC}"
    echo "  Fedora:         sudo dnf install python3"
    echo "  Ubuntu/Debian:  sudo apt install python3"
    exit 1
fi

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo -e "${RED}✗ Python ${PYTHON_VER} is too old. Python 3.10+ is required.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python ${PYTHON_VER}${NC}"

# Firefox
if command -v firefox &>/dev/null; then
    echo -e "${GREEN}✓ Firefox found${NC}"
else
    echo -e "${YELLOW}⚠ Firefox not found — required for scraping.${NC}"
    echo "    Fedora:         sudo dnf install firefox"
    echo "    Ubuntu/Debian:  sudo apt install firefox"
fi

# geckodriver
if command -v geckodriver &>/dev/null; then
    echo -e "${GREEN}✓ geckodriver found${NC}"
else
    echo -e "${YELLOW}⚠ geckodriver not found — required for scraping.${NC}"
    echo "    Fedora:         sudo dnf install geckodriver"
    echo "    Ubuntu/Debian:  sudo apt install firefox-geckodriver"
fi

echo ""

# ── Step 1: Virtual environment ───────────────────────────────────────────────

echo -e "${BOLD}[1/5] Setting up virtual environment...${NC}"

if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    python3 -m venv "$SCRIPT_DIR/.venv"
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${CYAN}  Already exists, skipping${NC}"
fi

echo ""

# ── Step 2: Install Python dependencies ──────────────────────────────────────

echo -e "${BOLD}[2/5] Installing dependencies...${NC}"

"$SCRIPT_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$SCRIPT_DIR/.venv/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"

echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# ── Step 3: Directories and data files ───────────────────────────────────────

echo -e "${BOLD}[3/5] Setting up data directories...${NC}"
echo ""

# logging/
mkdir -p "$SCRIPT_DIR/logging"

# config/
mkdir -p "$SCRIPT_DIR/config"

# config/booking_urls.json (city search URLs)
CITY_COUNT=0
if [ -f "$SCRIPT_DIR/config/booking_urls.json" ]; then
    CITY_COUNT=$(python3 -c "import json; d=json.load(open('$SCRIPT_DIR/config/booking_urls.json')); print(len(d))" 2>/dev/null || echo 0)
fi

if [ "$CITY_COUNT" -gt 0 ]; then
    echo -e "The repository includes ${BOLD}${CITY_COUNT} pre-configured city URL(s)${NC}."
    read -p "Keep existing city search URLs? [Y/n]: " KEEP_URLS
    if [[ "$KEEP_URLS" =~ ^[Nn]$ ]]; then
        echo '{}' > "$SCRIPT_DIR/config/booking_urls.json"
        echo -e "${CYAN}  City URLs cleared — add cities via the app${NC}"
    else
        echo -e "${GREEN}✓ Keeping existing city URLs${NC}"
    fi
else
    mkdir -p "$SCRIPT_DIR/config"
    echo '{}' > "$SCRIPT_DIR/config/booking_urls.json"
    echo -e "${GREEN}✓ Empty city list created — add cities via the app${NC}"
fi

echo ""

# base/ (hotel database)
mkdir -p "$SCRIPT_DIR/base"
HOTEL_FILES=$(find "$SCRIPT_DIR/base" -name "*.json" 2>/dev/null | wc -l)

if [ "$HOTEL_FILES" -gt 0 ]; then
    echo -e "The repository includes ${BOLD}${HOTEL_FILES} hotel database file(s)${NC}."
    read -p "Keep existing hotel database? [Y/n]: " KEEP_BASE
    if [[ "$KEEP_BASE" =~ ^[Nn]$ ]]; then
        rm -f "$SCRIPT_DIR/base/"*.json
        echo -e "${CYAN}  Hotel database cleared — will be populated by scraping${NC}"
    else
        echo -e "${GREEN}✓ Keeping existing hotel database${NC}"
    fi
else
    echo -e "${CYAN}  Hotel database is empty — will be populated by scraping${NC}"
fi

echo ""

# ── Step 4: Google Sheets integration ────────────────────────────────────────

echo -e "${BOLD}[4/5] Google Sheets integration${NC}"
echo ""
echo -e "The app can automatically sync newly found hotels to a Google Spreadsheet."
echo ""
read -p "Enable Google Sheets integration? [y/N]: " ENABLE_GSHEETS
echo ""

GSHEETS_ENABLED=false

if [[ "$ENABLE_GSHEETS" =~ ^[Yy]$ ]]; then
    GSHEETS_ENABLED=true

    echo -e "Enter your ${BOLD}Google Spreadsheet ID${NC}."
    echo -e "  (It's the long string in the spreadsheet URL:"
    echo -e "   https://docs.google.com/spreadsheets/d/${BOLD}YOUR_SPREADSHEET_ID${NC}/edit)"
    echo ""
    read -p "Spreadsheet ID: " GSHEET_ID

    cat > "$SCRIPT_DIR/.env" <<EOF
GSHEET_ID="${GSHEET_ID}"
KEY_PATH="gsheet_key.json"
EOF

    echo ""
    echo -e "${GREEN}✓ Google Sheets ID saved${NC}"
    echo ""
    echo -e "${YELLOW}${BOLD}── Action required: place your credentials file ──────────────────────${NC}"
    echo ""
    echo -e "The app needs a Google service account JSON key to access your spreadsheet."
    echo -e "Place the file here after installation:"
    echo ""
    echo -e "    ${BOLD}$SCRIPT_DIR/config/gsheet_key.json${NC}"
    echo ""
    echo -e "If you don't have a credentials file yet:"
    echo -e "  1. Open Google Cloud Console → IAM & Admin → Service Accounts"
    echo -e "  2. Create a service account, generate a JSON key and download it"
    echo -e "  3. Share your spreadsheet with the service account e-mail (Editor access)"
    echo -e "  4. Rename the downloaded file to ${BOLD}gsheet_key.json${NC} and place it in:"
    echo -e "     ${BOLD}$SCRIPT_DIR/config/${NC}"
    echo ""
    echo -e "${YELLOW}──────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    read -p "Press Enter to continue..."
else
    # Create .env with empty values so the app doesn't crash on import
    cat > "$SCRIPT_DIR/.env" <<'EOF'
GSHEET_ID=""
KEY_PATH=""
EOF
    echo -e "${CYAN}  Google Sheets disabled — new hotels will only be saved locally${NC}"
fi

echo ""

# ── Step 5: Desktop launcher ──────────────────────────────────────────────────

echo -e "${BOLD}[5/5] Creating desktop launcher...${NC}"

DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_DIR/hotel-scraper.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Hotel Scraper
Comment=Booking.com hotel scraper with Google Sheets integration
Exec=$SCRIPT_DIR/.venv/bin/python3 $SCRIPT_DIR/gui.py
Icon=$SCRIPT_DIR/icon.png
Terminal=false
Categories=Utility;
StartupWMClass=hotel-scraper
StartupNotify=true
EOF

chmod +x "$DESKTOP_DIR/hotel-scraper.desktop"
chmod +x "$SCRIPT_DIR/run_hotel_scrap.sh"

if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

echo -e "${GREEN}✓ Desktop launcher created${NC}"
echo ""

# ── Done ──────────────────────────────────────────────────────────────────────

echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║          Installation complete! ✓            ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Launch ${BOLD}Hotel Scraper${NC}:"
echo -e "  • Application menu — search for ${BOLD}Hotel Scraper${NC}"
echo -e "  • Terminal:  ${BOLD}bash $SCRIPT_DIR/run_hotel_scrap.sh${NC}"
echo ""

if $GSHEETS_ENABLED && [ ! -f "$SCRIPT_DIR/config/gsheet_key.json" ]; then
    echo -e "${YELLOW}⚠ Don't forget to place your Google credentials file at:${NC}"
    echo -e "    ${BOLD}$SCRIPT_DIR/config/gsheet_key.json${NC}"
    echo ""
fi
