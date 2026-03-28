# Hotel Scraper

A desktop application for automated hotel data collection from Booking.com.
Supports multiple cities, stores a local hotel database, and can automatically sync new properties to Google Sheets.

---

## Features

- **Modern GUI** — dark-themed interface built with CustomTkinter
- **Selenium + Firefox** — real browser engine, handles dynamic pages and bot protection
- **Headless mode** — scrape in the background without opening a browser window
- **City management** — add, edit, and remove cities directly from the app
- **Local database** — hotel history stored in JSON files, duplicates are skipped automatically
- **Google Sheets sync** — new hotels are appended to your spreadsheet automatically (optional)
- **Live logs** — color-coded log output displayed inside the app in real time

---

## Requirements

| Component | Version |
|-----------|---------|
| Python | 3.10+ |
| Firefox | any recent version |
| geckodriver | matching your Firefox version |

Install system dependencies if needed:

```bash
# Fedora
sudo dnf install python3 firefox geckodriver

# Ubuntu / Debian
sudo apt install python3 firefox firefox-geckodriver
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/MirTrudMike/HOTELS_scrap.git
cd HOTELS_scrap
```

### 2. Run the install script

```bash
bash install.sh
```

The script will interactively:

- create a virtual environment and install all dependencies
- offer to pre-configure cities (Tbilisi, Gudauri, Yerevan) or start with an empty list
- ask whether you want Google Sheets integration (see below)
- create a desktop launcher in your application menu

After installation, launch the app from the application menu (search for **Hotel Scraper**) or run:

```bash
bash run_hotel_scrap.sh
```

---

## Google Sheets Integration

If you enabled Google Sheets during installation, complete these two steps.

### 1. Create a Google service account

1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable **Google Sheets API**: APIs & Services → Enable APIs → Google Sheets API
4. Go to **IAM & Admin → Service Accounts**
5. Create a service account, open it → **Keys → Add Key → JSON**
6. Download the generated JSON key file

### 2. Grant access to your spreadsheet

1. Open your Google Spreadsheet
2. Click **Share** and add the service account email with **Editor** access
   (the email looks like `name@project-id.iam.gserviceaccount.com` — it's inside the JSON file)

### 3. Place the credentials file

Rename the downloaded JSON file to `gsheet_key.json` and place it here:

```
HOTELS_scrap/
└── config/
    └── gsheet_key.json   ← here
```

The app is now ready. Each scraping run will automatically append newly discovered hotels to your spreadsheet — one sheet per city.

---

## Project Structure

```
HOTELS_scrap/
├── gui.py                  # GUI application (main entry point)
├── main.py                 # CLI version
├── install.sh              # Installation script
├── run_hotel_scrap.sh      # Launch script
├── requirements.txt        # Python dependencies
├── icon.png                # Application icon
│
├── config/
│   ├── booking_urls.json   # Booking.com search URLs per city
│   ├── logging_config.py   # Logging setup
│   └── gsheet_key.json     # Google credentials (not in repo — add manually)
│
├── scraper/
│   ├── scraper.py          # Selenium scraper
│   ├── parser.py           # Hotel card parser
│   ├── storage.py          # Local database management
│   ├── sheets.py           # Google Sheets integration
│   └── models.py           # HotelData dataclass
│
├── base/                   # Local hotel database (JSON files)
│   └── {City}_hotels.json
│
└── logging/                # Log files (created automatically)
```

---

## Adding a New City

1. Open the app
2. Click **+** next to the city list in the left panel
3. Enter the city name and its Booking.com search URL

You can get the search URL directly from your browser's address bar after setting up filters on Booking.com.

---

## Hotel Data Fields

| Field | Description |
|-------|-------------|
| `id` | Unique Booking.com property identifier |
| `name` | Hotel name |
| `stars` | Star rating (0–5) |
| `rating` | Guest score |
| `number_of_reviews` | Total review count |
| `district` | City district |
| `city` | City name |
| `new_mark` | "New to Booking.com" badge flag |
| `date_parsed` | Date first discovered |
| `link` | Hotel page URL |
| `foto` | Hotel photo URL |
