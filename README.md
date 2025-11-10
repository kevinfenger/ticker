# Sports Display Setup Guide

## Initial Setup (No WiFi Configured)

1. **Power on the device**
2. **Look for WiFi network**: `SportsDisplay-Setup`
3. **Connect with password**: `sports123`
4. **Open web browser** and go to: `http://192.168.4.1`
5. **Fill out the form**:
   - WiFi network name and password
   - Choose your sports conference
   - API URL (usually can leave default)
6. **Click "Save Settings & Restart"**
7. **Device will restart** and connect to your WiFi

## Changing Settings Later

If you need to change settings after initial setup:

1. **Option A - File Edit**: Edit `settings.toml` directly on the CIRCUITPY drive
2. **Option B - Force Setup Mode**: 
   - Delete or rename `settings.toml` 
   - Restart the device
   - Follow initial setup steps above

## Settings File Format

Your `settings.toml` should look like this:

```toml
# Comments are supported
CIRCUITPY_WIFI_SSID = "YourNetworkName"
CIRCUITPY_WIFI_PASSWORD = "YourPassword"
CIRCUITPY_WEB_API_PORT = 80
CIRCUITPY_WEB_API_PASSWORD = "passw0rd"
TIMEZONE = "America/Denver"

# Sports API Configuration  
API_BASE_URL = "http://143.110.202.154:8000/api/live"
DETAILED_CONFERENCES = "big_sky"
```

## Conference Options

- `big_sky` - Big Sky Conference
- `big_ten` - Big Ten
- `sec` - SEC
- `acc` - ACC  
- `big_12` - Big 12
- `pac_12` - Pac-12

## API URL Configuration

The API URL supports several parameters:
- Base: `http://143.110.202.154:8000/api/live`
- With conference: `http://143.110.202.154:8000/api/live?detailed_conferences=big_sky`
- With page size: `http://143.110.202.154:8000/api/live?detailed_conferences=big_sky&page_size=10`

## Display Settings

- **Timezone**: Adjusts game times to your local timezone
- **Display Time**: Each game shows for 8 seconds by default
- **Border Color**: Currently set to dim blue for power savings
- **Refresh Rate**: Automatically fetches new data based on number of games

## Troubleshooting

**Setup mode not appearing?**
- Make sure `adafruit_httpserver` is in your `lib/` folder
- Check that WiFi credentials are missing or incorrect in `settings.toml`
- Look for "Starting setup mode..." message in serial console

**Can't connect to setup network?**
- Try restarting the device
- Look for network named exactly: `SportsDisplay-Setup`
- Password is: `sports123`
- Wait 30-60 seconds after power-on for setup network to appear

**Setup page won't load?**
- Try `http://192.168.4.1` 
- Make sure you're connected to the SportsDisplay-Setup network
- Wait a few seconds after connecting for the device to fully start
- Try refreshing the page or clearing browser cache

**WiFi connection fails after setup?**
- Double-check network name and password in setup form
- Make sure your WiFi network is 2.4GHz (not 5GHz only)
- Check if your network has special characters that need escaping

**No sports data showing?**
- Check that device is connected to WiFi (look for IP address in console)
- Verify API URL is correct in settings
- Check conference setting matches available games
- Try different conference if no games are found

## Required Libraries

Make sure these are in your `lib/` folder:
- `adafruit_httpserver/` - For setup web interface
- `adafruit_bitmap_font/` - For custom fonts
- `adafruit_display_text/` - For text display
- `adafruit_imageload/` - For team logos
- `adafruit_requests.mpy` - For API calls
- `adafruit_connection_manager.mpy` - Dependency
- `adafruit_bus_device/` - Dependency
- `adafruit_ticks.mpy` - Dependency
- `neopixel.mpy` - Status LED

## Files Structure

```
/CIRCUITPY/
├── code.py              # Main sports display program
├── setup.py             # Configuration web server  
├── settings.toml        # Configuration file (created by setup)
├── README.md           # This file
├── fonts/              # Font files (4x6.bdf, 5x7.bdf, 6x10.bdf)
├── logos/              # Team and league logos
│   ├── leagues/        # NBA.bmp, NFL.bmp, etc.
│   ├── nba/           # Team logos
│   ├── nfl/           # Team logos
│   └── college/       # College team logos
└── lib/               # Required CircuitPython libraries
```

## Power Saving Features

The display includes several power optimizations:
- Dimmed border colors (blue instead of bright white)
- No college league logos (large and power-hungry)
- Smaller random team bitmaps (16x16 instead of 24x24)
- Efficient color choices for maximum visibility with minimal power

## Support

If you encounter issues:
1. Check the serial console output for error messages
2. Verify all required files and libraries are present  
3. Test with a simple WiFi network (no special characters)
4. Try different conference settings if no games appear
5. Check API status by visiting the API URL in a web browser