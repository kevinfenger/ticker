# Static Sports Score Display for LED Matrix
# Shows one game at a time on 64x32 display with API data
# Multi-board configuration for horizontal display

import time
import board
import displayio
import framebufferio
import vectorio
import random
import wifi
import socketpool
import ssl
import os
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
import adafruit_imageload
import terminalio
import adafruit_requests
import rgbmatrix

# Version and Update Configuration
VERSION = "1.0.0"  # Current version - update this with each release
GITHUB_REPO = "kevinfenger/ticker"  # Your actual repo - create a release to test updates
GITHUB_API_BASE = "https://api.github.com/repos"

def check_disk_space():
    """Check available disk space for update operations"""
    try:
        # Get filesystem stats
        statvfs = os.statvfs("/")
        
        # Calculate sizes in KB for easier reading
        block_size = statvfs[0]  # Fragment size
        total_blocks = statvfs[2]  # Total blocks
        free_blocks = statvfs[3]   # Available blocks
        
        total_kb = (total_blocks * block_size) // 1024
        free_kb = (free_blocks * block_size) // 1024
        used_kb = total_kb - free_kb
        
        print(f"Disk Space Analysis:")
        print(f"  Total: {total_kb} KB ({total_kb/1024:.1f} MB)")
        print(f"  Used:  {used_kb} KB ({used_kb/1024:.1f} MB)")
        print(f"  Free:  {free_kb} KB ({free_kb/1024:.1f} MB)")
        print(f"  Usage: {(used_kb/total_kb)*100:.1f}%")
        
        # Check current file sizes for backup planning
        try:
            code_size = os.stat("/code.py")[6]
            setup_size = os.stat("/setup.py")[6]
            print(f"Current Files:")
            print(f"  code.py:  {code_size} bytes ({code_size/1024:.1f} KB)")
            print(f"  setup.py: {setup_size} bytes ({setup_size/1024:.1f} KB)")
            
            # Calculate space needed for safe updates
            backup_space_needed = code_size + setup_size  # bytes
            temp_space_needed = code_size + setup_size    # bytes for new versions
            total_update_space = backup_space_needed + temp_space_needed
            
            print(f"Update Space Requirements:")
            print(f"  Backup space needed: {backup_space_needed} bytes ({backup_space_needed/1024:.1f} KB)")
            print(f"  Temp download space: {temp_space_needed} bytes ({temp_space_needed/1024:.1f} KB)")
            print(f"  Total for safe updates: {total_update_space} bytes ({total_update_space/1024:.1f} KB)")
            
            # Check if we have enough space
            free_bytes = free_kb * 1024
            if free_bytes > total_update_space * 1.5:  # 50% safety margin
                print(f"✓ Sufficient space for safe updates (with 50% margin)")
                return True
            else:
                print(f"⚠ WARNING: Limited space for updates. Consider cleaning up files.")
                return False
                
        except OSError as e:
            print(f"Could not check file sizes: {e}")
            return False
            
    except Exception as e:
        print(f"Disk space check failed: {e}")
        return False

def check_github_releases():
    """Check GitHub for available releases"""
    try:
        #print(f"Checking GitHub releases for {GITHUB_REPO}...")
        
        # GitHub API endpoint for latest release
        url = f"{GITHUB_API_BASE}/{GITHUB_REPO}/releases/latest"
        
        # Make request with timeout
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            release_data = response.json()
            
            latest_version = release_data.get('tag_name', 'unknown')
            release_name = release_data.get('name', 'Unnamed Release')
            release_notes = release_data.get('body', 'No release notes available')
            published_at = release_data.get('published_at', 'Unknown date')
            is_prerelease = release_data.get('prerelease', False)
            
            #print(f"Latest release found: {latest_version}")
            #print(f"Current version: {VERSION}")
            
            # Basic version comparison (assumes semantic versioning)
            if latest_version != VERSION and not is_prerelease:
                #print(f"✓ Update available: {latest_version}")
                return {
                    'available': True,
                    'version': latest_version,
                    'name': release_name,
                    'notes': release_notes,
                    'published': published_at,
                    'download_url': None  # We'll add file download URLs next
                }
            else:
                #print("✓ Running latest version")
                return {
                    'available': False,
                    'version': latest_version,
                    'current': VERSION
                }
                
        elif response.status_code == 404:
            #print("Repository found but no releases published yet")
            return {'error': 'No releases found - create your first release on GitHub'}
        else:
            #print(f"GitHub API error: {response.status_code}")
            return {'error': f'API returned {response.status_code}'}
            
    except Exception as e:
        print(f"Error checking for updates: {e}")
        return {'error': str(e)}

TIMEZONE = os.getenv("TIMEZONE") 
try: 
    FONT = bitmap_font.load_font("/fonts/6x10.bdf")
except:
    FONT = terminalio.FONT

try:
    SMALLER_FONT = bitmap_font.load_font("/fonts/5x7.bdf")
except:
    SMALLER_FONT = terminalio.FONT

try:
    SMALLEST_FONT = bitmap_font.load_font("/fonts/4x6.bdf")
except:
    SMALLEST_FONT = terminalio.FONT

# Character limits based on font choice
# terminalio.FONT: ~8 chars for 64px width
# font5x8.bin: ~12-13 chars for 64px width (much better!)


displayio.release_displays()

# Colors
TEXT_WHITE = 0xC0C0C0  # Power-efficient white (75% brightness instead of 100%)
TEXT_GREEN = 0x00FF00
TEXT_RED = 0xFF0000
TEXT_YELLOW = 0xFFFF00
TEXT_CYAN = 0x00FFFF

# Matrix setup
matrix_width = 64
matrix_height = 32
chain_across = 4
tile_down = 1
display_width = matrix_width * chain_across
display_height = matrix_height * tile_down

matrix = rgbmatrix.RGBMatrix(
    width=display_width, 
    height=display_height, 
    bit_depth=2,  # Restored to 2 for better color depth and logo quality
        rgb_pins=[
        board.MTX_R1,
        board.MTX_G1,
        board.MTX_B1,
        board.MTX_R2,
        board.MTX_G2,
        board.MTX_B2
    ],
    addr_pins=[
        board.MTX_ADDRA,
        board.MTX_ADDRB,
        board.MTX_ADDRC,
        board.MTX_ADDRD
    ],
    clock_pin=board.MTX_CLK,
    latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE,
    tile=tile_down, serpentine=False,
    doublebuffer=True)  # Enable double buffering for smoother updates 

display = framebufferio.FramebufferDisplay(matrix)

# Calculate board centers dynamically based on chain_across and matrix_width
board_centers = []
for i in range(chain_across):
    center_x = (i * matrix_width) + (matrix_width // 2)
    board_centers.append(center_x)

#print(f"Board centers: {board_centers}")  # Debug output

# API settings - Build URL dynamically from settings
def build_api_url():
    """Build API URL from settings.toml configuration"""
    # Get base API URL from settings or use default
    base_api = os.getenv('API_BASE_URL', 'http://143.110.202.154:8000/api/live')
    
    # Get collections settings
    collections = os.getenv('COLLECTIONS', '')
    
    # If we have collections configured, build detailed URL
    if collections:
        api_url = f"{base_api}?collections={collections}&page_size=10"
        print(f"Using detailed API URL: {api_url}")
        return api_url
    else:
        # Use simple live endpoint
        if '?' not in base_api:
            api_url = f"{base_api}?page_size=10"
        else:
            api_url = f"{base_api}&page_size=10"
        print(f"Using basic API URL: {api_url}")
        return api_url

API_URL = build_api_url()
BASE_URL = "http://143.110.202.154/"
UPDATE_INTERVAL = 30  # seconds between API calls
DISPLAY_TIME = 10  # seconds to show each game

# Initialize config server variable
config_server = None

def show_config_url_on_display(url, update_info=None):
    """Temporarily show configuration URL and update info on the LED display with logo"""
    #print(f"Showing config URL on display: {url}")
    #if update_info and update_info.get('available'):
    #   print(f"Also showing update notification: v{update_info.get('version')}")
    
    # Create a temporary group for the URL display
    url_group = displayio.Group()
    
    # Board 1 - Company branding with logo and border
    # Left border line
    border_line = vectorio.Rectangle(pixel_shader=displayio.Palette(1), width=2, height=32, x=2, y=0)
    border_line.pixel_shader[0] = TEXT_CYAN  # Cyan border
    url_group.append(border_line)
    
    try:
        # Load the wild deer logo first (will be in background)
        logo_bitmap, logo_palette = adafruit_imageload.load("/logos/display/wild_deer.bmp")
        
        # Create first logo - positioned at far left
        logo_tilegrid1 = displayio.TileGrid(logo_bitmap, pixel_shader=logo_palette)
        logo_width = logo_bitmap.width
        logo_height = logo_bitmap.height
        logo_tilegrid1.x = 4   # All the way to the left (after border)
        logo_tilegrid1.y = 1   # Top position
        
        # Create second logo - positioned next to the first one
        logo_tilegrid2 = displayio.TileGrid(logo_bitmap, pixel_shader=logo_palette)
        logo_tilegrid2.x = 4 + logo_width + 1  # Next to first logo with 1-pixel gap (moved left 1 pixel)
        logo_tilegrid2.y = 1   # Same height
        
        # Add both logos (background layer)
        url_group.append(logo_tilegrid1)
        url_group.append(logo_tilegrid2)
        
        # Company name added after logo (foreground layer - will appear on top)
        company_name = label.Label(SMALLER_FONT, text="WildDeer SD", color=TEXT_WHITE, scale=1)
        company_name.anchor_point = (0.0, 0.0)
        company_name.anchored_position = (6, 2)  # Top position - will display over logo
        url_group.append(company_name)
        
    except Exception as e:
        # Fallback - just show company name on board 1 (centered)
        company_name = label.Label(SMALLER_FONT, text="WildDeer SD", color=TEXT_WHITE, scale=1)
        company_name.anchor_point = (0.0, 0.0)
        company_name.anchored_position = (6, 12)  # Vertically centered
        url_group.append(company_name)
    
    # Boards 2-4 - Configuration information
    config_start_x = 68  # Start of board 2
    
    # Configuration title
    config_title = label.Label(SMALLER_FONT, text="Configuration Portal", color=TEXT_GREEN, scale=1)
    config_title.anchor_point = (0.0, 0.0)
    config_title.anchored_position = (config_start_x, 4)  # Back to original position (more to the left)
    url_group.append(config_title)
    
    # Instructions
    instruction_label = label.Label(SMALLER_FONT, text="See or make changes here:", color=TEXT_WHITE, scale=1)
    instruction_label.anchor_point = (0.0, 0.0)
    instruction_label.anchored_position = (config_start_x + 4, 14)  # Add spacing to the right
    url_group.append(instruction_label)
    
    # URL display
    url_label = label.Label(SMALLER_FONT, text=f"http://{url}", color=TEXT_GREEN, scale=1)
    url_label.anchor_point = (0.0, 0.0)
    url_label.anchored_position = (config_start_x, 24)
    url_group.append(url_label)
    
    # Update notification (if available) - use board 4 only with compact text
    if update_info and update_info.get('available'):
        board4_start_x = 203  # 3 more pixels right (was 200, now 203)
        
        # Line 1: "Update Avail" - compact notification
        update_title = label.Label(SMALLEST_FONT, text="Update Avail", color=TEXT_YELLOW, scale=1)
        update_title.anchor_point = (0.0, 0.0)
        update_title.anchored_position = (board4_start_x, 2)  # 4 pixels up (was 6, now 2)
        url_group.append(update_title)
        
        # Line 2: "@configSite" - instruction to visit config (@ symbol bigger)
        at_symbol = label.Label(SMALLER_FONT, text="@", color=TEXT_CYAN, scale=1)
        at_symbol.anchor_point = (0.0, 0.0)
        at_symbol.anchored_position = (board4_start_x, 10)  # 4 pixels up (was 14, now 10)
        url_group.append(at_symbol)
        
        config_text = label.Label(SMALLEST_FONT, text="configSite", color=TEXT_CYAN, scale=1)
        config_text.anchor_point = (0.0, 0.0)
        config_text.anchored_position = (board4_start_x + 6, 11)  # Offset to align with @ symbol baseline
        url_group.append(config_text)
    
    # Show the URL display
    display.root_group = url_group
    
    # Wait 10 seconds
    time.sleep(10)

def show_setup_mode_on_display(ap_ip):
    """Show setup mode information on the LED display"""
    print(f"Showing setup mode info on display: {ap_ip}")
    
    # Create a temporary group for the setup display
    setup_group = displayio.Group()
    
    # Name label
    name_label = label.Label(SMALLER_FONT, text="Name:", color=TEXT_YELLOW, scale=1)
    name_label.anchor_point = (0.0, 0.0)
    name_label.anchored_position = (120, 2)
    setup_group.append(name_label)
    
    # WiFi network name
    network_label = label.Label(SMALLER_FONT, text="SportsDisplay-Setup", color=TEXT_WHITE, scale=1)
    network_label.anchor_point = (0.0, 0.0)
    network_label.anchored_position = (150, 2)  # Offset to the right of "Name:" label
    setup_group.append(network_label)
    
    # PW label
    pw_label = label.Label(SMALLER_FONT, text="PW:", color=TEXT_YELLOW, scale=1)
    pw_label.anchor_point = (0.0, 0.0)
    pw_label.anchored_position = (120, 9)  # Close under the network name
    setup_group.append(pw_label)
    
    # Password 
    password_label = label.Label(SMALLER_FONT, text="sports123", color=TEXT_WHITE, scale=1)
    password_label.anchor_point = (0.0, 0.0)
    password_label.anchored_position = (150, 9)  # Aligned with network name, close under it
    setup_group.append(password_label)
    
    # Board 1 - Instructions (left side)
    # Row 2: "Connect To Wifi:" instruction - vertically centered between network name and password
    connect_instruction = label.Label(SMALLER_FONT, text="Connect To Wifi:", color=TEXT_CYAN, scale=1)
    connect_instruction.anchor_point = (0.0, 0.0)
    connect_instruction.anchored_position = (2, 5)  # Moved up 3 pixels for better centering
    setup_group.append(connect_instruction)
    
    # Row 3: "Then Visit to Config:" instruction  
    config_instruction = label.Label(SMALLER_FONT, text="Then Visit to Config:", color=TEXT_CYAN, scale=1)
    config_instruction.anchor_point = (0.0, 0.0)
    config_instruction.anchored_position = (2, 22)
    setup_group.append(config_instruction)
    
    # Row 3: IP address aligned with "Then Visit to Config:"
    ip_label = label.Label(SMALLER_FONT, text=f"http://{ap_ip}:5000", color=TEXT_GREEN, scale=1)
    ip_label.anchor_point = (0.0, 0.0)
    ip_label.anchored_position = (120, 22)  # Start after board 1
    setup_group.append(ip_label)
    
    # Show the setup display
    display.root_group = setup_group
    
    # Wait 15 seconds to show the info (a bit longer since there's more info)
    #time.sleep(15)
    
    print("Setup mode display timeout, setup server running")

# Check disk space before starting main operations
#print("Checking disk space...")
#sufficient_space = check_disk_space()

# Connect to WiFi
print("Connecting to WiFi...")
try:
    ssid = os.getenv('CIRCUITPY_WIFI_SSID')
    password = os.getenv('CIRCUITPY_WIFI_PASSWORD')
    
    if not ssid or not password:
        raise Exception("WiFi credentials not configured")
    
   # print(f"Attempting to connect to: {ssid}")
    wifi.radio.connect(ssid, password)
    #print(f"Connected to WiFi! IP: {wifi.radio.ipv4_address}")
    wifi_connected = True
    
    pool = socketpool.SocketPool(wifi.radio)
    requests = adafruit_requests.Session(pool, ssl.create_default_context())
    
    # Check for available updates
   # print(f"WildDeer Sports Display {VERSION}")
    update_info = check_github_releases()
    #if update_info.get('available'):
    #    print(f"🔄 Update available: {update_info['version']}")
    #    print("Visit the configuration page to install updates")
   # elif update_info.get('error'):
    #    print(f"Could not check for updates: {update_info['error']}")
    
    # Start configuration server alongside main display
    try:
        #print("Starting configuration server...")
        import setup
        config_server = setup.start_config_server(setup_mode=False, pool=pool)
        #print(f"start_config_server returned: {config_server}")
        #print(f"config_server type: {type(config_server)}")
        if config_server:
            #print(f"Configuration available at: http://{wifi.radio.ipv4_address}:5000")
            # Show config URL on LED display for 10 seconds, including update info if available
            show_config_url_on_display(f"{wifi.radio.ipv4_address}:5000", update_info)
        else:
            print("Could not start configuration server - returned None")
    except Exception as config_error:
        print(f"Could not start config server: {config_error}")
        config_server = None
except Exception as e:
    #print(f"WiFi connection failed: {e}")
    #print("Starting setup mode...")
    
    try:
        # Import and run setup server
        import setup
        
        # Create access point first to get IP address
        #print("Creating WiFi Access Point...")
        wifi.radio.start_ap("SportsDisplay-Setup", "sports123")
        
        # Wait for AP IP address to be assigned (retry with delay)
        ap_ip = None
        for retry in range(5):  # Try up to 5 times
            ap_ip_raw = wifi.radio.ipv4_address_ap
            if ap_ip_raw is not None:
                ap_ip = str(ap_ip_raw)
                break
            #print(f"Waiting for AP IP assignment... (attempt {retry + 1}/5)")
            time.sleep(1)
        
        if ap_ip is None:
            #print("ERROR: Could not get AP IP address after retries")
            ap_ip = "UNKNOWN"
        
        #print(f"Access Point created: SportsDisplay-Setup")
        #print(f"Password: sports123")
        #print(f"Connect and visit: http://{ap_ip}:5000")
        
        # Show setup mode info on display with IP address
        show_setup_mode_on_display(ap_ip)
        
        # Start the setup server (this will be blocking, but AP is already created)
        setup.start_config_server(setup_mode=True)
        
        # If we get here, setup completed and device should restart
        # But just in case, we'll continue with offline mode
    except Exception as setup_error:
        print(f"Setup mode failed: {setup_error}")
        print("Continuing in offline mode...")
    
    wifi_connected = False

def fetch_sports_data(url=None):
    """Get sports data from API"""
    if not wifi_connected:
        return [{
            "away_team": {"abbreviation": "NO", "score": "DATA"},
            "home_team": {"abbreviation": "NO", "score": "DATA"},
            "status": "Final",
            "sport_display": "No Data"
        }], None
    
    try:
        # Use provided URL or default API URL
        if url:
            # If url is relative (starts with /), append to base URL
            if url.startswith('/'):
                request_url = BASE_URL + url
            else:
                request_url = url
        else:
            request_url = API_URL
            
        print(f"Requesting: {request_url}")
        response = requests.get(request_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            games = data.get('data', [])
            
            # Get pagination info
            pagination = data.get('pagination', {})
            next_page_url = pagination.get('next_page_url')
            
            print(f"Fetched {len(games)} games. Next page: {next_page_url}")
            return games, next_page_url
        return [], None
    except Exception as e:
        print(f"API error: {e}")
        return [], None

def format_game_time(game_time_str):
    """Format game start time for display, converting to Mountain Time and including day"""
    try:
        # Parse the game time (assuming ISO format from API in UTC)
        if 'T' in game_time_str:
            date_part, time_part = game_time_str.split('T')
            
            # Parse the date part (YYYY-MM-DD)
            year, month, day = date_part.split('-')
            year, month, day = int(year), int(month), int(day)
            
            # Calculate day of week using Zeller's congruence (simplified)
            # 0=Saturday, 1=Sunday, 2=Monday, ..., 6=Friday
            if month < 3:
                month += 12
                year -= 1
            
            day_of_week_num = (day + ((13 * (month + 1)) // 5) + year + (year // 4) - (year // 100) + (year // 400)) % 7
            day_names = ["Sat", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri"]
            day_name = day_names[day_of_week_num]
            
            if ':' in time_part:
                # Remove timezone info if present (Z or +00:00)
                time_clean = time_part.replace('Z', '').split('+')[0].split('-')[0]
                hour_min = time_clean[:5]  # Get HH:MM
                hour, minute = hour_min.split(':')
                hour = int(hour)
                
                # Convert UTC to Mountain Time (UTC-7 in summer, UTC-6 in winter)
                # For simplicity, using UTC-7 (Mountain Daylight Time)
                hour -= 7  # Convert UTC to Mountain Time
                
                # Handle day rollover
                day_offset = 0
                if hour < 0:
                    hour += 24
                    day_offset = -1
                elif hour >= 24:
                    hour -= 24
                    day_offset = 1
                
                # Adjust day name if time conversion caused day change
                if day_offset != 0:
                    adjusted_day_num = (day_of_week_num + day_offset) % 7
                    day_name = day_names[adjusted_day_num]
                
                # Convert to 12-hour format
                if hour == 0:
                    time_str = f"12:{minute}AM"
                elif hour < 12:
                    time_str = f"{hour}:{minute}AM"
                elif hour == 12:
                    time_str = f"12:{minute}PM"
                else:
                    time_str = f"{hour-12}:{minute}PM"
                
                return f"{day_name} {time_str}"
    except Exception as e:
        print(f"Time parsing error: {e}")
        pass
    
    # Fallback - return original or "TBD"
    return "TBD"

def format_pro_team_name(team_name, sport):
    """Format professional team names to prioritize nickname over city"""
    if not team_name or not sport:
        return team_name
    
    # Only apply to professional leagues
    if sport not in ['NBA', 'NFL', 'MLB', 'NHL']:
        return team_name
    
    try:
        # Common city abbreviations for professional teams
        city_abbreviations = {
            'New Orleans': 'NO',
            'Golden State': 'GS',
            'Los Angeles': 'LA', 
            'New York': 'NY',
            'San Francisco': 'SF',
            'San Antonio': 'SA',
            'Oklahoma City': 'OKC',
            'Portland Trail': 'POR', 
            'Tampa Bay': 'TB',
            'Green Bay': 'GB',
            'Kansas City': 'KC',
            'Las Vegas': 'LV',
            'New England': 'NE',
        }
        
        # Split team name to find city and nickname
        parts = team_name.split()
        if len(parts) <= 1:
            return team_name
        
        # Try to identify if this follows "City Nickname" pattern
        # Look for common patterns
        if len(parts) >= 2:
            # Check if first part(s) match a city we want to abbreviate
            for city, abbrev in city_abbreviations.items():
                if team_name.startswith(city):
                    # Replace the city with abbreviation and keep the rest
                    nickname = team_name[len(city):].strip()
                    return f"{abbrev} {nickname}"
            
            # For other teams, try to detect city vs nickname
            # If first word is long (>6 chars), it's likely a city we should shorten
            first_word = parts[0]
            if len(first_word) > 6 and len(parts) >= 2:
                # Take first 3 characters of city + nickname
                nickname = ' '.join(parts[1:])
                return f"{first_word[:3]} {nickname}"
        
        return team_name
        
    except Exception as e:
        print(f"Team name formatting error: {e}")
        return team_name

def get_team_font(team_text):
    """Select appropriate font based on team text length"""
    # Define length threshold - if text is longer than this, use smaller font
    FONT_SWITCH_THRESHOLD = 8
    
    if len(team_text) > FONT_SWITCH_THRESHOLD:
        return SMALLER_FONT  # 5x7.bdf - smaller, more characters fit
    else:
        return FONT  # 6x10.bdf - larger, better readability

def load_league_logo(sport_short):
    """Load league logo bitmap, return TileGrid or None if not found"""
    try:
        # Map sport to league logo filename
        league_logo_map = {
            'NBA': 'NBA.bmp',
            'NFL': 'NFL.bmp', 
            'MLB': 'MLB.bmp',
            'NHL': 'NHL.bmp',
            'MBB': 'college.bmp',  # College Basketball uses college logo
            'WBB': 'college.bmp',
            'CFB': 'college.bmp'   # College Football uses college logo
        }
        
        logo_filename = league_logo_map.get(sport_short)
        
        if not logo_filename:
            return None
            
        logo_path = f"/logos/leagues/{logo_filename}"
        
        # Load the bitmap
        bitmap, palette = adafruit_imageload.load(logo_path, bitmap=displayio.Bitmap, palette=displayio.Palette)
        
        # Brighten dark colors in the palette for better LED visibility
        brightened_palette = brighten_logo_palette(palette)
        
        # Create a slightly smaller bitmap (reduce both dimensions by 15%)
        new_width = int(bitmap.width * 0.85)  # Reduce width by 15%
        new_height = int(bitmap.height * 0.85)  # Reduce height by 15%
        
        # Create scaled bitmap
        scaled_bitmap = displayio.Bitmap(new_width, new_height, len(brightened_palette))
        
        # Scale down both dimensions of the original bitmap
        for y in range(new_height):
            for x in range(new_width):
                # Sample from the original bitmap with proper scaling
                original_x = int(x * bitmap.width / new_width)
                original_y = int(y * bitmap.height / new_height)
                original_pixel = bitmap[original_x, original_y]
                scaled_bitmap[x, y] = original_pixel
        
        # Create a TileGrid to display the scaled bitmap
        tile_grid = displayio.TileGrid(scaled_bitmap, pixel_shader=brightened_palette)
        
        return tile_grid
        
    except Exception as e:
        return None

def load_team_logo(team_abbrev, sport_short):
    """Load team logo bitmap, return TileGrid or None if not found"""
    try:
        # Map sport to directory
        sport_dir_map = {
            'NBA': 'nba',
            'NFL': 'nfl', 
            'MLB': 'mlb',
            'NHL': 'nhl',
            'MBB': 'college',  # Mens College Basketball
            'WBB': 'college',  # Womens College Basketball
            'CFB': 'college'   # College Football
        }
        
        sport_dir = sport_dir_map.get(sport_short)
        
        if not sport_dir:
            return None
            
        logo_path = f"/logos/{sport_dir}/{team_abbrev}.bmp"
        
        # Load the bitmap
        bitmap, palette = adafruit_imageload.load(logo_path, bitmap=displayio.Bitmap, palette=displayio.Palette)
        
        # Brighten dark colors in the palette for better LED visibility
        brightened_palette = brighten_logo_palette(palette)
        
        # Create a slightly smaller bitmap (reduce height by 15%)
        new_width = bitmap.width
        new_height = int(bitmap.height * 0.85)  # Reduce height by 15%
        
        # Create scaled bitmap
        scaled_bitmap = displayio.Bitmap(new_width, new_height, len(brightened_palette))
        
        # Scale down only the height of the original bitmap
        for y in range(new_height):
            for x in range(new_width):
                # Sample from the original bitmap with height scaling
                original_y = int(y * bitmap.height / new_height)
                original_pixel = bitmap[x, original_y]
                scaled_bitmap[x, y] = original_pixel
        
        # Create a TileGrid to display the scaled bitmap
        tile_grid = displayio.TileGrid(scaled_bitmap, pixel_shader=brightened_palette)
        
        return tile_grid
        
    except Exception as e:
        return None

def generate_random_team_bitmap(team_abbrev, width=28, height=28, team_color=None):
    """Generate a random bitmap pattern for teams without logos using actual team colors"""
    try:
        # Create a palette with team colors
        palette = displayio.Palette(8)
        
        # Use team abbreviation to seed patterns for consistency
        team_hash = sum(ord(c) for c in team_abbrev.upper()) if team_abbrev else 42
        random.seed(team_hash)  # Seed with team name for consistency
        
        # Build color palette based on actual team color or fallback
        if team_color:
            # Use actual team color as primary
            primary_color = team_color
            
            # Extract RGB components to create variations
            r = (primary_color >> 16) & 0xFF
            g = (primary_color >> 8) & 0xFF
            b = primary_color & 0xFF
            
            # Create variations of the team color for the palette
            palette[0] = 0x000000  # Black background
            palette[1] = primary_color  # Primary team color
            palette[2] = ((r // 2) << 16) | ((g // 2) << 8) | (b // 2)  # Darker version
            palette[3] = 0xFFFFFF  # White accent
            palette[4] = ((min(255, r + 40)) << 16) | ((min(255, g + 40)) << 8) | (min(255, b + 40))  # Lighter version
            palette[5] = ((r // 3) << 16) | ((g // 3) << 8) | (b // 3)  # Much darker
            palette[6] = ((min(255, r + 80)) << 16) | ((min(255, g + 80)) << 8) | (min(255, b + 80))  # Much lighter
            palette[7] = primary_color  # Duplicate primary for extra weight
        else:
            # Fallback to generic color scheme if no team color available
            palette[0] = 0x000000  # Black
            palette[1] = 0x808080  # Gray
            palette[2] = 0x404040  # Dark gray
            palette[3] = 0xFFFFFF  # White
            palette[4] = 0xC0C0C0  # Light gray
            palette[5] = 0x202020  # Very dark gray
            palette[6] = 0xE0E0E0  # Very light gray
            palette[7] = 0x808080  # Gray duplicate
        
        # Create bitmap
        bitmap = displayio.Bitmap(width, height, len(palette))
        
        # Initialize entire bitmap with black background
        for y in range(height):
            for x in range(width):
                bitmap[x, y] = 0  # Black background
        
        # Define inner area with padding (create blank space around edges)
        padding = max(4, min(width, height) // 6)  # At least 4 pixels padding, or 1/6 of size
        inner_width = width - (2 * padding)
        inner_height = height - (2 * padding)
        
        # Only draw patterns in the inner area
        if inner_width > 0 and inner_height > 0:
            # Generate pattern based on team name
            pattern_type = team_hash % 4
            
            if pattern_type == 0:
                # Diagonal stripes - only in inner area
                for y in range(inner_height):
                    for x in range(inner_width):
                        actual_x = x + padding
                        actual_y = y + padding
                        stripe = (x + y) % 6
                        if stripe < 2:
                            bitmap[actual_x, actual_y] = 1  # Primary color
                        elif stripe < 4:
                            bitmap[actual_x, actual_y] = 2  # Secondary color
                        # else: leave as background (black)
        
            elif pattern_type == 1:
                # Checkerboard with center accent - only in inner area
                for y in range(inner_height):
                    for x in range(inner_width):
                        actual_x = x + padding
                        actual_y = y + padding
                        # Center circle area (relative to inner area)
                        center_x, center_y = inner_width // 2, inner_height // 2
                        dist_sq = (x - center_x) ** 2 + (y - center_y) ** 2
                        if dist_sq <= (min(inner_width, inner_height) // 4) ** 2:
                            bitmap[actual_x, actual_y] = 3  # Center accent
                        elif (x // 3 + y // 3) % 2:
                            bitmap[actual_x, actual_y] = 1  # Primary
                        else:
                            bitmap[actual_x, actual_y] = 2  # Secondary
        
            elif pattern_type == 2:
                # Concentric rectangles - only in inner area
                for y in range(inner_height):
                    for x in range(inner_width):
                        actual_x = x + padding
                        actual_y = y + padding
                        border_dist = min(x, y, inner_width - 1 - x, inner_height - 1 - y)
                        color_index = (border_dist % 4)
                        if color_index == 0:
                            bitmap[actual_x, actual_y] = 0  # Keep as background
                        else:
                            bitmap[actual_x, actual_y] = color_index
        
            else:
                # Random dots with structure - only in inner area
                for y in range(inner_height):
                    for x in range(inner_width):
                        actual_x = x + padding
                        actual_y = y + padding
                        # Create semi-random but structured pattern
                        noise = (x * 3 + y * 7 + team_hash) % 17
                        if noise < 4:
                            bitmap[actual_x, actual_y] = 1
                        elif noise < 8:
                            bitmap[actual_x, actual_y] = 2
                        elif noise < 10:
                            bitmap[actual_x, actual_y] = 3
                        # else: leave as background (black)
        
        # Add border around the logo for better visual alignment with real logos
        border_type = team_hash % 3  # 0=square, 1=circle, 2=thick square
        border_color = 2  # Use darker version of team color (power saving)
        
        if border_type == 0 or border_type == 2:
            # Square border (single or thick)
            thickness = 1 if border_type == 0 else 2
            for t in range(thickness):
                # Top and bottom borders
                for x in range(width):
                    if t < height:
                        bitmap[x, t] = border_color  # Use darker team color for border
                    if (height - 1 - t) >= 0:
                        bitmap[x, height - 1 - t] = border_color
                
                # Left and right borders
                for y in range(height):
                    if t < width:
                        bitmap[t, y] = border_color
                    if (width - 1 - t) >= 0:
                        bitmap[width - 1 - t, y] = border_color
        
        elif border_type == 1:
            # Circular border
            center_x, center_y = width // 2, height // 2
            radius = min(width, height) // 2 - 1
            
            for y in range(height):
                for x in range(width):
                    # Calculate distance from center
                    dist_sq = (x - center_x) ** 2 + (y - center_y) ** 2
                    dist = int(dist_sq ** 0.5)
                    
                    # Create circle border (2 pixels thick)
                    if radius - 2 <= dist <= radius:
                        bitmap[x, y] = border_color  # Use darker team color for border
        
        # Create TileGrid
        tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
        return tile_grid
        
    except Exception as e:
        print(f"DEBUG - Could not generate random bitmap for {team_abbrev}: {e}")
        return None

def format_game_status(game):
    """Format game status for display, return (status_text, status_color) tuple"""
    # Safety check for None game
    if game is None:
        return "NO DATA", TEXT_WHITE
    
    status = game.get('status', 'Unknown')
    game_time = game.get('date')
    
    # Determine status display with proper formatting
    if status == "In Progress":
        # Show quarter/period and time remaining for live games
        game_details = game.get('game_details') or {}
        period = game_details.get('period', '')
        time_remaining = game_details.get('clock', '')
        if period and time_remaining:
            status_text = f"{period} {time_remaining}"[:12]  # Increased from 8 to 12
        elif period:
            status_text = period[:12]  # Increased from 8 to 12
        else:
            status_text = "LIVE"
        status_color = TEXT_GREEN
    elif status == "Final":
        status_text = "FINAL"
        status_color = TEXT_YELLOW
    elif status.upper() in ['SCHEDULED', 'PRE'] or "Scheduled" in status:
        # For scheduled games, show start time
        if game_time:
            status_text = format_game_time(game_time)
            status_color = TEXT_CYAN
        else:
            status_text = "SCHED"
            status_color = TEXT_CYAN
    else:
        status_text = status[:8]
        status_color = TEXT_WHITE
    
    return status_text, status_color

def format_player_name(full_name):
    """Format player name as first initial + last name (e.g., 'K. Fenger')"""
    if not full_name or full_name == 'Player':
        return 'Player'
    
    try:
        # Split the name by spaces
        name_parts = full_name.strip().split()
        
        if len(name_parts) == 1:
            # Only one name part, return as is (truncated if needed)
            return name_parts[0][:12]
        elif len(name_parts) >= 2:
            # First initial + last name
            first_initial = name_parts[0][0].upper() if name_parts[0] else ''
            last_name = name_parts[-1]  # Use the last part as surname
            if len(last_name) <= 3: 
                if len(name_parts) == 3: # likely a Jr. Sr. or III suffix
                    last_name = name_parts[-2]  # Use the second to last part as surname
            formatted = f"{first_initial}. {last_name}"
            return formatted[:12]  # Truncate to fit display with expanded space
        else:
            return full_name[:12]
    except (IndexError, AttributeError):
        return 'Player'

def hex_to_rgb(hex_color):
    """Convert hex color string (e.g., '002a5c') to 24-bit integer color (0x002a5c)"""
    if not hex_color:
        return None
    
    # Remove '#' if present and ensure it's 6 characters
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return None
    
    try:
        # Convert hex string directly to 24-bit integer
        color_int = int(hex_color, 16)
        
        # Brighten the color if it's too dark
        return brighten_color(color_int)
    except ValueError:
        return None

def brighten_color(color_int, min_brightness=120, threshold=90):
    """Brighten a 24-bit color if it's too dark for LED matrix visibility"""
    # Extract RGB components
    r = (color_int >> 16) & 0xFF
    g = (color_int >> 8) & 0xFF
    b = color_int & 0xFF
    
    # Check if the color is too dark and brighten it
    max_component = max(r, g, b)
    if max_component > 0 and max_component < threshold:
        # Brighten dark colors by multiplying by a factor
        brightness_factor = min_brightness / max_component
        r = min(255, int(r * brightness_factor))
        g = min(255, int(g * brightness_factor))
        b = min(255, int(b * brightness_factor))
    
    return (r << 16) | (g << 8) | b

def brighten_logo_palette(palette):
    """Brighten dark colors in logo palette for better LED matrix visibility"""
    try:
        # Skip index 0 (usually background/transparent) and process other colors
        for i in range(1, len(palette)):
            original_color = palette[i]
            brightened_color = brighten_color(original_color)
            
            # Handle white/light colors specially for better logo text visibility
            if original_color == 0xFFFFFF:
                # Keep pure white as bright white for logo text (like OSU letters)
                brightened_color = 0xF0F0F0  # Slightly dimmed but still very bright
            elif brightened_color == 0xFFFFFF:
                # If brighten_color made something pure white, use bright white
                brightened_color = 0xF0F0F0  # Bright but power-efficient
            elif original_color >= 0xE0E0E0:
                # Very light colors (like off-white) should stay bright for visibility
                brightened_color = max(0xE0E0E0, brightened_color)
            
            palette[i] = brightened_color
        
        return palette
    except Exception as e:
        # If brightness adjustment fails, return original palette
        print(f"Palette brightness adjustment failed: {e}")
        return palette

def get_team_color(team_abbr, away_team, home_team):
    """Get team color from game data, returning RGB tuple or default color"""
    # Check if team_abbr matches away or home team
    away_abbrev = away_team.get('abbreviation', '')
    home_abbrev = home_team.get('abbreviation', '')
    
    if team_abbr == away_abbrev:
        return hex_to_rgb(away_team.get('color'))
    elif team_abbr == home_abbrev:
        return hex_to_rgb(home_team.get('color'))
    
    return None  # Return None if no match or no color

def update_game_display(game):
    """Update existing display labels with new game data - no recreation needed"""
    global current_game_performers, current_home_color, current_away_color, current_home_abbrev_global, current_away_abbrev_global
    
    # Safety check for None game
    if game is None:
        print("Warning: Received None game in update_game_display")
        return

    max_chars_with_rank= 10  # Allow for "#15 Duke" format - same as unranked
    max_chars_no_rank = 10   # More generous for unranked teams
    
    if not game:
        return
    
    # Extract game data
    sport = game.get('sport_display', '')
    if 'NBA' in sport:
        sport_short = 'NBA'
    elif 'NHL' in sport:
        sport_short = 'NHL'
    elif 'NFL' in sport:
        sport_short = 'NFL'
    elif 'MLB' in sport:
        sport_short = 'MLB'
    elif 'College' in sport and 'Basketball Mens' in sport:
        sport_short = 'MBB'
    elif 'College' in sport and 'Basketball Womens' in sport:
        sport_short = 'WBB'
    elif 'College' in sport and 'Football' in sport:
        sport_short = 'CFB'
    elif 'Soccer' in sport:
        sport_short = 'SOC'
    else:
        sport_short = sport.split()[0][:3].upper() if sport else 'GAM'
    
    status = game.get('status', 'Unknown')
    away_team = game.get('away_team', {})
    home_team = game.get('home_team', {})
    game_time = game.get('date')
    
    # Get formatted status and color
    status_text, status_color = format_game_status(game)
    
    # Get team info
    away = away_team.get('name', away_team.get('abbreviation', 'Away Team'))
    home = home_team.get('name', home_team.get('abbreviation', 'Home Team'))
    
    # Apply professional team formatting for NBA, NFL, MLB, NHL
    away = format_pro_team_name(away, sport_short)
    home = format_pro_team_name(home, sport_short)
    
    away_score = away_team.get('score', '0')
    home_score = home_team.get('score', '0')
    away_rank = away_team.get('rank')
    home_rank = home_team.get('rank')
    
    # Truncate team names to fit display, accounting for rankings and font choice
    # Determine character limits based on which font would be optimal
    away_font = get_team_font(away)
    home_font = get_team_font(home)
    
    # Adjust character limits based on font choice
    # 5x7 font (SMALLER_FONT) allows more characters than 6x10 font (FONT)
    away_char_limit = 12 if away_font == SMALLER_FONT else max_chars_with_rank if away_rank is not None else max_chars_no_rank
    home_char_limit = 12 if home_font == SMALLER_FONT else max_chars_with_rank if home_rank is not None else max_chars_no_rank
    
    if away_rank is not None:
        away_display = f"#{away_rank} {away}"[:away_char_limit]
    else:
        away_display = away[:away_char_limit]
        
    if home_rank is not None:
        home_display = f"#{home_rank} {home}"[:home_char_limit]
    else:
        home_display = home[:home_char_limit]
    
    # Update Board 1: League logo (left) + Sport name (right, bold)
    sport_label.text = sport_short
    
    # Load and position league logo
    global sport_logo_tile
    display_group = display.root_group
    
    league_logo = load_league_logo(sport_short)
    if league_logo:
        # Position league logo further left on Board 1 (adjusted for smaller size and left border)
        logo_x = board_centers[0] - 31  # Moved right by 1 pixel to clear the left border
        logo_y = (display_height // 2) - 14  # Adjusted for 15% smaller logo height (~27px instead of 32px)
        league_logo.x = logo_x
        league_logo.y = logo_y
        
        # Remove old league logo if it exists
        if sport_logo_tile and sport_logo_tile in display_group:
            display_group.remove(sport_logo_tile)
            
        display_group.append(league_logo)
        sport_logo_tile = league_logo
    else:
        # Remove league logo if sport doesn't have one
        if sport_logo_tile and sport_logo_tile in display_group:
            display_group.remove(sport_logo_tile)
            sport_logo_tile = None
    
    # Update Combined Boards 2+3: Team logos, period/status, and score
    # Get team abbreviations for logo display
    home_abbrev = home_team.get('abbreviation', home[:3].upper())
    away_abbrev = away_team.get('abbreviation', away[:3].upper())
    
    # Get team colors for display elements and store globally
    home_color = get_team_color(home_abbrev, away_team, home_team)
    away_color = get_team_color(away_abbrev, away_team, home_team)
    
    # Store colors and abbreviations globally for Board 4 scrolling
    current_home_color = home_color
    current_away_color = away_color
    current_home_abbrev_global = home_abbrev
    current_away_abbrev_global = away_abbrev
    
    # Update team abbreviations with individual colors (Away vs Home format)
    home_abbrev_label.text = home_abbrev  # Home team on right side
    away_abbrev_label.text = away_abbrev  # Away team on left side
    
    # Apply team colors to individual team labels
    if away_color:
        away_abbrev_label.color = away_color  # Left side shows away team
    else:
        away_abbrev_label.color = TEXT_WHITE
    
    if home_color:
        home_abbrev_label.color = home_color  # Right side shows home team
    else:
        home_abbrev_label.color = TEXT_WHITE
    
    # Update rank indicators (small numbers above team names) - Away vs Home layout
    away_rank_label.text = f"#{away_rank}" if away_rank is not None else ""  # Left side shows away team rank
    home_rank_label.text = f"#{home_rank}" if home_rank is not None else ""  # Right side shows home team rank
    
    # Try to load team logos
    global home_team_logo_tile, away_team_logo_tile
    display_group = display.root_group
    
    # Load away team logo (positioned towards left edge - away team now on left)
    home_logo = load_team_logo(away_abbrev, sport_short)
    if not home_logo: 
        home_logo = generate_random_team_bitmap(away_abbrev, team_color=away_color)
    if home_logo:
        # Position the logo towards the left side of board 2 (moved closer to center)
        logo_x = board_centers[1] - 30  # Less extreme left positioning
        logo_y = (display_height // 2) - 14  # Adjusted for 15% smaller logo height (~27px instead of 32px)
        home_logo.x = logo_x
        home_logo.y = logo_y
        
        # Remove old home logo if it exists
        if home_team_logo_tile and home_team_logo_tile in display_group:
            display_group.remove(home_team_logo_tile)
        # Remove text label if it exists
        if home_team_logo_label in display_group:
            display_group.remove(home_team_logo_label)
            
        display_group.append(home_logo)
        home_team_logo_tile = home_logo
    else:
        # Fallback to generated random bitmap
        # Remove old home logo if it exists
        if home_team_logo_tile and home_team_logo_tile in display_group:
            display_group.remove(home_team_logo_tile)
            home_team_logo_tile = None
        # Remove text label if it exists
        if home_team_logo_label in display_group:
            display_group.remove(home_team_logo_label)
        if home_team_logo_label not in display_group:
            display_group.append(home_team_logo_label)
        home_team_logo_label.text = away_abbrev
        # Apply team color to text label
        if away_color:
            home_team_logo_label.color = away_color
        else:
            home_team_logo_label.color = TEXT_WHITE
    
    # Load home team logo (positioned towards right edge - home team now on right)
    away_logo = load_team_logo(home_abbrev, sport_short)
    if not away_logo: 
        away_logo = generate_random_team_bitmap(home_abbrev, team_color=home_color)
    if away_logo:
        # Position the logo towards the right side of board 3 (moved closer to center)
        away_logo.x = board_centers[2] - 2  # Less extreme right positioning
        away_logo.y = (display_height // 2) - 14  # Adjusted for 15% smaller logo height (~27px instead of 32px)
        
        # Remove old away logo if it exists
        if away_team_logo_tile and away_team_logo_tile in display_group:
            display_group.remove(away_team_logo_tile)
        # Remove text label if it exists
        if away_team_logo_label in display_group:
            display_group.remove(away_team_logo_label)
            
        display_group.append(away_logo)
        away_team_logo_tile = away_logo
    else:
        # Ultimate fallback to text if bitmap generation fails
        # Remove old away logo if it exists
        if away_team_logo_tile and away_team_logo_tile in display_group:
            display_group.remove(away_team_logo_tile)
            away_team_logo_tile = None
        
        if away_team_logo_label not in display_group:
            display_group.append(away_team_logo_label)
        away_team_logo_label.text = home_abbrev
        # Apply team color to text label
        if home_color:
            away_team_logo_label.color = home_color
        else:
            away_team_logo_label.color = TEXT_WHITE
    
    # Update period/status in top center
    game_period_label.text = status_text
    game_period_label.color = status_color
    
    # Update score in bottom center (Away - Home format to match display)
    game_score_label.text = f"{away_score} - {home_score}"
    
    # Update Board 4: Prepare performers for cycling
    top_performers = game.get('top_performers', [])
    current_game_performers = top_performers if top_performers else []
    
    if current_game_performers and len(current_game_performers) > 0:
        # Show first performer initially
        performer = current_game_performers[0]
        name = format_player_name(performer.get('player_name', 'Player'))
        team_abbr = performer.get('team_abbr', '')
        stat_value = performer.get('value', '')
        stat_type = performer.get('stat_category', '')[:3]
        
        # Truncate float values to 1 decimal place
        try:
            if '.' in str(stat_value):
                stat_value = f"{float(stat_value):.1f}"
        except (ValueError, TypeError):
            pass
        
        # Set team color for the stats header team label using global colors for consistency
        if team_abbr == current_home_abbrev_global and current_home_color:
            board4_stats_team_label.color = current_home_color
        elif team_abbr == current_away_abbrev_global and current_away_color:
            board4_stats_team_label.color = current_away_color
        else:
            board4_stats_team_label.color = TEXT_CYAN
        
        board4_stats_team_label.text = team_abbr
        board4_player_label.text = name
        board4_stat_label.text = f"{stat_value} {stat_type}"
        #print(f"Game: {sport_short} {status_text} | {away_abbrev} {away_score} - {home_score} {home_abbrev} | {len(current_game_performers)} performers available")
    else:
        board4_stats_team_label.text = ""
        board4_player_label.text = "NO DATA"
        board4_stat_label.text = ""
        #print(f"Game: {sport_short} {status_text} | {away_abbrev} {away_score} - {home_score} {home_abbrev} | No performers")


# Initialize
current_game = 0
games = []
next_page_url = None
last_update = 0
last_change = time.monotonic()

# Stats display variables
current_game_performers = []  # Store current game's performers

# Global team colors for current game (used for persistent Board 4 coloring)
current_home_color = None
current_away_color = None
current_home_abbrev_global = ""
current_away_abbrev_global = ""

# Global label references for efficient updates
sport_label = None
sport_logo_tile = None       # League logo on Board 1
home_team_logo_label = None  # Left side of combined boards 2+3 (text fallback)
home_team_logo_tile = None   # Left side logo bitmap
away_team_logo_label = None  # Right side of combined boards 2+3 (text fallback)
away_team_logo_tile = None   # Right side logo bitmap
away_abbrev_label = None     # Away team abbreviation (left side)
vs_label = None              # "vs" text between teams
home_abbrev_label = None     # Home team abbreviation (right side)
away_rank_label = None       # Small rank indicator for away team (left side)
home_rank_label = None       # Small rank indicator for home team (right side)
game_period_label = None  # Middle top of combined boards 2+3
game_score_label = None  # Middle bottom of combined boards 2+3
board4_stats_title = None
board4_stats_team_label = None  # Team label next to "STATS" title
board4_player_label = None
board4_stat_label = None


def setup_display_layout():
    """Create the display layout once with all labels"""
    global sport_label, sport_logo_tile, home_team_logo_label, game_period_label, home_rank_label, away_rank_label
    global game_score_label, away_team_logo_label, board4_stats_title, board4_stats_team_label, board4_player_label, board4_stat_label
    global home_team_logo_tile, away_team_logo_tile, away_abbrev_label, vs_label, home_abbrev_label
    
    main_group = displayio.Group()
    
    # BOARD 1: League logo (left) + Sport name (right, bold)
    # League logo will be added dynamically based on sport
    # Sport text using smaller font with moderate scale for better size control
    sport_label = label.Label(SMALLER_FONT, text="", color=TEXT_CYAN, scale=2)
    sport_label.anchor_point = (1.0, 0.5)  # Right aligned
    sport_label.anchored_position = (board_centers[0] + 32, display_height // 2)  # Moved even further right
    main_group.append(sport_label)
    
    # BOARDS 2+3 COMBINED: Team logos, period/status, and score
    # Calculate the center of the combined boards 2+3 area
    combined_center_x = (board_centers[1] + board_centers[2]) // 2
    
    # Add top and bottom border lines spanning entire boards 2+3 width
    border_left = 64   # Start of board 2
    border_right = 192  # End of board 3
    border_width = border_right - border_left
    
    # Create border using top and bottom lines only
    border_palette = displayio.Palette(1)
    border_palette[0] = 0x002040  # Even dimmer blue - very easy on eyes, still visible
    
    # Top border (moved up by 2 pixels to the very top)
    top_border = vectorio.Rectangle(pixel_shader=border_palette, width=border_width, height=1, x=border_left, y=0)
    main_group.append(top_border)
    
    # Bottom border (moved down by 1 pixel closer to bottom)  
    bottom_border = vectorio.Rectangle(pixel_shader=border_palette, width=border_width, height=1, x=border_left, y=display_height-1)
    main_group.append(bottom_border)
    
    # Add borders for Board 1 (left border + top/bottom)
    board1_left = 0
    board1_right = 64
    board1_width = board1_right - board1_left
    
    # Board 1 top border
    board1_top_border = vectorio.Rectangle(pixel_shader=border_palette, width=board1_width, height=1, x=board1_left, y=0)
    main_group.append(board1_top_border)
    
    # Board 1 bottom border
    board1_bottom_border = vectorio.Rectangle(pixel_shader=border_palette, width=board1_width, height=1, x=board1_left, y=display_height-1)
    main_group.append(board1_bottom_border)
    
    # Board 1 left border
    board1_left_border = vectorio.Rectangle(pixel_shader=border_palette, width=1, height=display_height, x=board1_left, y=0)
    main_group.append(board1_left_border)
    
    # Add borders for Board 4 (right border + top/bottom)
    board4_left = 192
    board4_right = 256
    board4_width = board4_right - board4_left
    
    # Board 4 top border
    board4_top_border = vectorio.Rectangle(pixel_shader=border_palette, width=board4_width, height=1, x=board4_left, y=0)
    main_group.append(board4_top_border)
    
    # Board 4 bottom border
    board4_bottom_border = vectorio.Rectangle(pixel_shader=border_palette, width=board4_width, height=1, x=board4_left, y=display_height-1)
    main_group.append(board4_bottom_border)
    
    # Board 4 right border
    board4_right_border = vectorio.Rectangle(pixel_shader=border_palette, width=1, height=display_height, x=board4_right-1, y=0)
    main_group.append(board4_right_border)
    
    # Left side: Home team (will be logo or text fallback) - positioned towards left side
    home_team_logo_label = label.Label(SMALLER_FONT, text="", color=TEXT_WHITE, scale=1)
    home_team_logo_label.anchor_point = (0.0, 0.5)  # Left aligned
    home_team_logo_label.anchored_position = (board_centers[1] - 20, display_height // 2)
    # Note: home_team_logo_label will be added to main_group only if no logo is available
    
    # Right side: Away team (will be logo or text fallback) - positioned towards right side
    away_team_logo_label = label.Label(SMALLER_FONT, text="", color=TEXT_WHITE, scale=1)
    away_team_logo_label.anchor_point = (1.0, 0.5)  # Right aligned
    away_team_logo_label.anchored_position = (board_centers[2] + 20, display_height // 2)
    # Note: away_team_logo_label will be added to main_group only if no logo is available
    
    # Center: Team abbreviations (AWAY vs HOME) - separate labels for individual colors
    away_abbrev_label = label.Label(SMALLER_FONT, text="", color=TEXT_WHITE, scale=1)
    away_abbrev_label.anchor_point = (1.0, 0.5)  # Right aligned
    away_abbrev_label.anchored_position = (combined_center_x - 8, display_height // 2 + 2)  # Left of center
    main_group.append(away_abbrev_label)
    
    vs_label = label.Label(SMALLER_FONT, text="vs", color=TEXT_WHITE, scale=1)
    vs_label.anchor_point = (0.5, 0.5)  # Center aligned
    vs_label.anchored_position = (combined_center_x, display_height // 2 + 2)  # Centered
    main_group.append(vs_label)
    
    home_abbrev_label = label.Label(SMALLER_FONT, text="", color=TEXT_WHITE, scale=1)
    home_abbrev_label.anchor_point = (0.0, 0.5)  # Left aligned
    home_abbrev_label.anchored_position = (combined_center_x + 8, display_height // 2 + 2)  # Right of center
    main_group.append(home_abbrev_label)
    
    # Small rank indicators positioned above team abbreviations
    global away_rank_label, home_rank_label
    away_rank_label = label.Label(SMALLEST_FONT, text="", color=TEXT_CYAN, scale=1)
    away_rank_label.anchor_point = (1.0, 1.0)  # Right-bottom aligned
    away_rank_label.anchored_position = (combined_center_x - 15, display_height // 2 - 1)  # Left of center, above team names
    main_group.append(away_rank_label)
    
    home_rank_label = label.Label(SMALLEST_FONT, text="", color=TEXT_CYAN, scale=1)
    home_rank_label.anchor_point = (0.0, 1.0)  # Left-bottom aligned  
    home_rank_label.anchored_position = (combined_center_x + 15, display_height // 2 - 1)  # Right of center, above team names
    main_group.append(home_rank_label)
    
    # Top: Period/time remaining or status
    game_period_label = label.Label(SMALLER_FONT, text="", color=TEXT_WHITE, scale=1)
    game_period_label.anchor_point = (0.5, 0.0)
    game_period_label.anchored_position = (combined_center_x, 2)
    main_group.append(game_period_label)
    
    # Bottom: Score (X - Y format)
    game_score_label = label.Label(FONT, text="", color=TEXT_YELLOW, scale=1)
    game_score_label.anchor_point = (0.5, 1.0)
    game_score_label.anchored_position = (combined_center_x, display_height)
    main_group.append(game_score_label)
    
    # BOARD 4: Stats title moved left with team label next to it
    board4_stats_title = label.Label(SMALLER_FONT, text="STATS", color=TEXT_CYAN, scale=1)
    board4_stats_title.anchor_point = (0.0, 0.0)  # Left aligned
    board4_stats_title.anchored_position = (board_centers[3] - 28, 2)  # 10 pixels more left than center
    main_group.append(board4_stats_title)
    
    board4_stats_team_label = label.Label(SMALLER_FONT, text="", color=TEXT_CYAN, scale=1)
    board4_stats_team_label.anchor_point = (0.0, 0.0)  # Left aligned
    board4_stats_team_label.anchored_position = (board_centers[3] + 5, 2)  # Next to STATS title
    main_group.append(board4_stats_team_label)
    
    board4_player_label = label.Label(SMALLER_FONT, text="", color=TEXT_WHITE, scale=1)
    board4_player_label.anchor_point = (0.5, 0.5)  # Center aligned for full width
    board4_player_label.anchored_position = (board_centers[3], 16)  # Center of board 4, expanded width
    main_group.append(board4_player_label)
    
    board4_stat_label = label.Label(SMALLER_FONT, text="", color=TEXT_GREEN, scale=1)
    board4_stat_label.anchor_point = (0.5, 1.0)
    board4_stat_label.anchored_position = (board_centers[3], 30)
    main_group.append(board4_stat_label)
    
    # Set the display once
    display.root_group = main_group
    #("Display layout created with combined boards 2+3")

def display_stats():
    """Display stats on Board 4 - cycle through up to X performers for DISPLAY_TIME / max_performers second each"""
    if not current_game_performers or len(current_game_performers) == 0:
        return
    
    max_performers = min(5, len(current_game_performers))
    sleep_time = DISPLAY_TIME / max_performers
    
    for i in range(max_performers):
        performer = current_game_performers[i]
        
        name = format_player_name(performer.get('player_name', 'Player'))
        team_abbr = performer.get('team_abbr', '')
        stat_value = performer.get('value', '')
        stat_type = performer.get('stat_category', '')[:3]
        
        # Truncate float values to 1 decimal place
        try:
            if '.' in str(stat_value):
                stat_value = f"{float(stat_value):.1f}"
        except (ValueError, TypeError):
            pass
        
        # Set team color for stats header team label using stored global colors
        if team_abbr == current_home_abbrev_global and current_home_color:
            board4_stats_team_label.color = current_home_color
        elif team_abbr == current_away_abbrev_global and current_away_color:
            board4_stats_team_label.color = current_away_color
        else:
            board4_stats_team_label.color = TEXT_WHITE
        
        # Update labels - stats team header, player name (center), stat bottom
        board4_stats_team_label.text = team_abbr
        board4_player_label.text = name
        board4_stat_label.text = f"{stat_value} {stat_type}"
        
        # Display for 1 second
        time.sleep(sleep_time)

# Create the display layout once
setup_display_layout()
# Main loop
while True:
    current_time = time.monotonic()
    
    # Poll configuration server if available
    if wifi_connected and config_server:
        try:
            result = config_server.poll()
        except Exception as poll_error:
            print(f"Config server poll error: {poll_error}")
    elif wifi_connected:
        # Debug: why isn't config_server available?
        if current_time - last_update < 10:  
            print(f"Config server not available: config_server={config_server}")

    timeout = min(len(games) * DISPLAY_TIME + 1, UPDATE_INTERVAL*3)  # Dynamic timeout when no more pages
        
    need_new_data = (
        len(games) == 0 or  # No games loaded yet
        (current_game >= len(games) and next_page_url and current_time - last_change >= DISPLAY_TIME) or  # Ready for next page
        (not next_page_url and current_time - last_update >= timeout)  or # Dynamic timeout only when no next page
        (current_time - last_update >= UPDATE_INTERVAL * 4)  # fallback max timeout
    )
    
    if need_new_data:
        url_to_fetch = next_page_url if next_page_url else None
        new_games, new_next_page_url = fetch_sports_data(url_to_fetch)
        
        if new_games:
            # Filter out any None games to prevent crashes
            games = [game for game in new_games if game is not None]
            next_page_url = new_next_page_url
            current_game = 0
            last_update = current_time
            # Force immediate display by resetting the timer to trigger cycling logic
            last_change = current_time - DISPLAY_TIME
        else:
            # If no new games and we have a next_page_url, reset to beginning
            if next_page_url:
                next_page_url = None
    
    # Show next game
    if games and current_time - last_change >= DISPLAY_TIME:
        if current_game < len(games) and games[current_game] is not None:
            update_game_display(games[current_game])
            display_stats()
        else:
            print(f"DEBUG: Skipping game {current_game} - out of range or None")
        current_game = current_game + 1  # Remove modulo - let pagination logic handle wraparound
        last_change = current_time
    
    time.sleep(0.1)  # Reduced sleep time since stats function handles its own timing
