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
import json
from adafruit_matrixportal.matrix import Matrix
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_display_text.scrolling_label import ScrollingLabel
import adafruit_imageload
import terminalio
import adafruit_requests
import neopixel
import rgbmatrix

# Timezone configuration
TIMEZONE = "America/Denver"  # Mountain Time - change as needed
# Common options: "America/New_York" (Eastern), "America/Chicago" (Central), 
#                 "America/Denver" (Mountain), "America/Los_Angeles" (Pacific)

# Main font for boards 1-3 (sport, teams, scores)
try: 
    FONT = bitmap_font.load_font("/fonts/6x10.bdf")
    print("Loaded 6x10.bdf for main display")
except:
    FONT = terminalio.FONT
    print("Using terminalio font for main display")

# Stats font for Board 4 only (compact stats)
try:
    STATS_FONT = bitmap_font.load_font("/fonts/5x7.bdf")
    print("Loaded 5x7.bdf for stats")
except:
    STATS_FONT = terminalio.FONT
    print("Using terminalio font for stats")

# Stats font for Board 4 only (compact stats)
try:
    SMALLEST_FONT = bitmap_font.load_font("/fonts/4x6.bdf")
    print("Loaded 4x6.bdf for smallest stats")
except:
    SMALLEST_FONT = terminalio.FONT
    print("Using terminalio font for smallest stats")

# Character limits based on font choice
# terminalio.FONT: ~8 chars for 64px width
# font5x8.bin: ~12-13 chars for 64px width (much better!)
MAX_CHARS_WITH_RANK = 10  # Allow for "#15 Duke" format - same as unranked
MAX_CHARS_NO_RANK = 10   # More generous for unranked teams

displayio.release_displays()

# Colors
TEXT_WHITE = 0xFFFFFF
TEXT_GREEN = 0x00FF00
TEXT_RED = 0xFF0000
TEXT_YELLOW = 0xFFFF00
TEXT_CYAN = 0x00FFFF

# Matrix setup
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness = 0.3, auto_write=True)

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

print(f"Board centers: {board_centers}")  # Debug output

# API settings
API_URL = "http://143.110.202.154:8000/api/live?detailed_conferences=big_sky"
BASE_URL = "http://http://143.110.202.154:8000/"
UPDATE_INTERVAL = 30  # seconds between API calls
DISPLAY_TIME = 8  # seconds to show each game

# Connect to WiFi
print("Connecting to WiFi...")
try:
    import os
    ssid = os.getenv('CIRCUITPY_WIFI_SSID')
    password = os.getenv('CIRCUITPY_WIFI_PASSWORD')
    
    wifi.radio.connect(ssid, password)
    print(f"Connected to WiFi!")
    wifi_connected = True
    
    pool = socketpool.SocketPool(wifi.radio)
    requests = adafruit_requests.Session(pool, ssl.create_default_context())
except Exception as e:
    print(f"WiFi failed: {e}")
    wifi_connected = False

def fetch_sports_data(url=None):
    """Get sports data from API"""
    if not wifi_connected:
        return [{
            "away_team": {"abbreviation": "LAL", "score": "98"},
            "home_team": {"abbreviation": "GSW", "score": "102"},
            "status": "Final",
            "sport_display": "Basketball NBA"
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
    """Format game start time for display, converting to Mountain Time"""
    try:
        # Parse the game time (assuming ISO format from API in UTC)
        if 'T' in game_time_str:
            date_part, time_part = game_time_str.split('T')
            if ':' in time_part:
                # Remove timezone info if present (Z or +00:00)
                time_clean = time_part.replace('Z', '').split('+')[0].split('-')[0]
                hour_min = time_clean[:5]  # Get HH:MM
                hour, minute = hour_min.split(':')
                hour = int(hour)
                
                # Convert UTC to Mountain Time (UTC-7 in summer, UTC-6 in winter)
                # For simplicity, using UTC-7 (Mountain Daylight Time)
                # You may want to adjust this based on daylight saving rules
                hour -= 7  # Convert UTC to Mountain Time
                
                # Handle day rollover
                if hour < 0:
                    hour += 24
                elif hour >= 24:
                    hour -= 24
                
                # Convert to 12-hour format
                if hour == 0:
                    return f"12:{minute}AM"
                elif hour < 12:
                    return f"{hour}:{minute}AM"
                elif hour == 12:
                    return f"12:{minute}PM"
                else:
                    return f"{hour-12}:{minute}PM"
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
            'Portland Trail': 'POR',  # Trail Blazers
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
        return STATS_FONT  # 5x7.bdf - smaller, more characters fit
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
            'MBB': 'college.bmp',  # College Basketball uses college logo
            'CFB': 'college.bmp'   # College Football uses college logo
        }
        
        logo_filename = league_logo_map.get(sport_short)
        
        if not logo_filename:
            return None
            
        logo_path = f"/logos/leagues/{logo_filename}"
        
        # Load the bitmap
        bitmap, palette = adafruit_imageload.load(logo_path, bitmap=displayio.Bitmap, palette=displayio.Palette)
        
        # Create a slightly smaller bitmap (reduce both dimensions by 15%)
        new_width = int(bitmap.width * 0.85)  # Reduce width by 15%
        new_height = int(bitmap.height * 0.85)  # Reduce height by 15%
        
        # Create scaled bitmap
        scaled_bitmap = displayio.Bitmap(new_width, new_height, len(palette))
        
        # Scale down both dimensions of the original bitmap
        for y in range(new_height):
            for x in range(new_width):
                # Sample from the original bitmap with proper scaling
                original_x = int(x * bitmap.width / new_width)
                original_y = int(y * bitmap.height / new_height)
                original_pixel = bitmap[original_x, original_y]
                scaled_bitmap[x, y] = original_pixel
        
        # Create a TileGrid to display the scaled bitmap
        tile_grid = displayio.TileGrid(scaled_bitmap, pixel_shader=palette)
        tile_grid = displayio.TileGrid(scaled_bitmap, pixel_shader=palette)
        
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
            'MBB': 'college',  # College Basketball
            'CFB': 'college'   # College Football
        }
        
        sport_dir = sport_dir_map.get(sport_short)
        
        if not sport_dir:
            return None
            
        logo_path = f"/logos/{sport_dir}/{team_abbrev}.bmp"
        
        # Load the bitmap
        bitmap, palette = adafruit_imageload.load(logo_path, bitmap=displayio.Bitmap, palette=displayio.Palette)
        
        # Create a slightly smaller bitmap (reduce height by 15%)
        new_width = bitmap.width
        new_height = int(bitmap.height * 0.85)  # Reduce height by 15%
        
        # Create scaled bitmap
        scaled_bitmap = displayio.Bitmap(new_width, new_height, len(palette))
        
        # Scale down only the height of the original bitmap
        for y in range(new_height):
            for x in range(new_width):
                # Sample from the original bitmap with height scaling
                original_y = int(y * bitmap.height / new_height)
                original_pixel = bitmap[x, original_y]
                scaled_bitmap[x, y] = original_pixel
        
        # Create a TileGrid to display the scaled bitmap
        tile_grid = displayio.TileGrid(scaled_bitmap, pixel_shader=palette)
        
        return tile_grid
        
    except Exception as e:
        print(f"DEBUG - Could not load logo for {team_abbrev} at {logo_path}: {e}")
        return None

def generate_random_team_bitmap(team_abbrev, width=16, height=16):
    """Generate a random bitmap pattern for teams without logos"""
    try:
        # Create a palette with team colors
        palette = displayio.Palette(8)
        
        # Base colors - adjust based on team abbreviation to get some consistency
        # Use team abbreviation to seed colors so same team gets same pattern
        team_hash = sum(ord(c) for c in team_abbrev.upper()) if team_abbrev else 42
        random.seed(team_hash)  # Seed with team name for consistency
        
        # Define some color sets
        color_sets = [
            [0x000000, 0xFF0000, 0x800000, 0xFFFFFF, 0x400000, 0xFF8080, 0x200000, 0xFFC0C0],  # Red theme
            [0x000000, 0x0000FF, 0x000080, 0xFFFFFF, 0x000040, 0x8080FF, 0x000020, 0xC0C0FF],  # Blue theme
            [0x000000, 0x00FF00, 0x008000, 0xFFFFFF, 0x004000, 0x80FF80, 0x002000, 0xC0FFC0],  # Green theme
            [0x000000, 0xFFFF00, 0x808000, 0xFFFFFF, 0x404000, 0xFFFF80, 0x202000, 0xFFFFC0],  # Yellow theme
            [0x000000, 0xFF8000, 0x804000, 0xFFFFFF, 0x402000, 0xFFC080, 0x201000, 0xFFE0C0],  # Orange theme
            [0x000000, 0x8000FF, 0x400080, 0xFFFFFF, 0x200040, 0xC080FF, 0x100020, 0xE0C0FF],  # Purple theme
        ]
        
        # Select color set based on team
        color_set = color_sets[team_hash % len(color_sets)]
        for i, color in enumerate(color_set):
            palette[i] = color
        
        # Create bitmap
        bitmap = displayio.Bitmap(width, height, len(palette))
        
        # Generate pattern based on team name
        pattern_type = team_hash % 4
        
        if pattern_type == 0:
            # Diagonal stripes
            for y in range(height):
                for x in range(width):
                    stripe = (x + y) % 6
                    if stripe < 2:
                        bitmap[x, y] = 1  # Primary color
                    elif stripe < 4:
                        bitmap[x, y] = 2  # Secondary color
                    else:
                        bitmap[x, y] = 0  # Background
        
        elif pattern_type == 1:
            # Checkerboard with center accent
            for y in range(height):
                for x in range(width):
                    # Center circle area
                    center_x, center_y = width // 2, height // 2
                    dist_sq = (x - center_x) ** 2 + (y - center_y) ** 2
                    if dist_sq <= (min(width, height) // 4) ** 2:
                        bitmap[x, y] = 3  # Center accent
                    elif (x // 3 + y // 3) % 2:
                        bitmap[x, y] = 1  # Primary
                    else:
                        bitmap[x, y] = 2  # Secondary
        
        elif pattern_type == 2:
            # Concentric rectangles
            for y in range(height):
                for x in range(width):
                    border_dist = min(x, y, width - 1 - x, height - 1 - y)
                    color_index = border_dist % 4
                    bitmap[x, y] = color_index
        
        else:
            # Random dots with structure
            for y in range(height):
                for x in range(width):
                    # Create semi-random but structured pattern
                    noise = (x * 3 + y * 7 + team_hash) % 17
                    if noise < 4:
                        bitmap[x, y] = 1
                    elif noise < 8:
                        bitmap[x, y] = 2
                    elif noise < 10:
                        bitmap[x, y] = 3
                    else:
                        bitmap[x, y] = 0
        
        # Create TileGrid
        tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
        print(f"DEBUG - Generated random bitmap for {team_abbrev}, pattern type {pattern_type}")
        return tile_grid
        
    except Exception as e:
        print(f"DEBUG - Could not generate random bitmap for {team_abbrev}: {e}")
        return None

def format_game_status(game):
    """Format game status for display, return (status_text, status_color) tuple"""
    status = game.get('status', 'Unknown')
    game_time = game.get('date')
    
    # Determine status display with proper formatting
    if status == "In Progress":
        # Show quarter/period and time remaining for live games
        game_details = game.get('game_details', {})
        print(game_details)
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
            return name_parts[0][:10]
        elif len(name_parts) >= 2:
            # First initial + last name
            first_initial = name_parts[0][0].upper() if name_parts[0] else ''
            last_name = name_parts[-1]  # Use the last part as surname
            formatted = f"{first_initial}. {last_name}"
            return formatted[:10]  # Truncate to fit display
        else:
            return full_name[:10]
    except (IndexError, AttributeError):
        return 'Player'

def update_game_display(game):
    """Update existing display labels with new game data - no recreation needed"""
    global current_game_performers
    
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
    elif 'College' in sport and 'Basketball' in sport:
        sport_short = 'MBB'
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
    # 5x7 font (STATS_FONT) allows more characters than 6x10 font (FONT)
    away_char_limit = 12 if away_font == STATS_FONT else MAX_CHARS_WITH_RANK if away_rank is not None else MAX_CHARS_NO_RANK
    home_char_limit = 12 if home_font == STATS_FONT else MAX_CHARS_WITH_RANK if home_rank is not None else MAX_CHARS_NO_RANK
    
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
    
    # Update team abbreviations in center
    team_abbrev_label.text = f"{home_abbrev} vs {away_abbrev}"
    
    # Update rank indicators (small numbers above team names)
    home_rank_label.text = f"#{home_rank}" if home_rank is not None else ""
    away_rank_label.text = f"#{away_rank}" if away_rank is not None else ""
    
    # Try to load team logos
    global home_team_logo_tile, away_team_logo_tile
    display_group = display.root_group
    
    # Load home team logo (positioned towards left edge)
    home_logo = load_team_logo(home_abbrev, sport_short)
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
            
        # Generate and position random bitmap
        random_logo = generate_random_team_bitmap(home_abbrev)
        if random_logo:
            logo_x = board_centers[1] - 30  # Same positioning as real logo
            logo_y = (display_height // 2) - 8  # Random bitmaps are now 16x16
            random_logo.x = logo_x
            random_logo.y = logo_y
            display_group.append(random_logo)
            home_team_logo_tile = random_logo
        else:
            # Ultimate fallback to text if bitmap generation fails
            if home_team_logo_label not in display_group:
                display_group.append(home_team_logo_label)
            home_team_logo_label.text = home_abbrev
    
    # Load away team logo (positioned towards right edge)
    away_logo = load_team_logo(away_abbrev, sport_short)
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
        # Fallback to generated random bitmap
        # Remove old away logo if it exists
        if away_team_logo_tile and away_team_logo_tile in display_group:
            display_group.remove(away_team_logo_tile)
            away_team_logo_tile = None
        
        # Remove text label if it exists
        if away_team_logo_label in display_group:
            display_group.remove(away_team_logo_label)
            
        # Generate and position random bitmap
        random_logo = generate_random_team_bitmap(away_abbrev)
        if random_logo:
            logo_x = board_centers[2] - 2  # Same positioning as real logo
            logo_y = (display_height // 2) - 8  # Random bitmaps are now 16x16
            random_logo.x = logo_x
            random_logo.y = logo_y
            display_group.append(random_logo)
            away_team_logo_tile = random_logo
        else:
            # Ultimate fallback to text if bitmap generation fails
            if away_team_logo_label not in display_group:
                display_group.append(away_team_logo_label)
            away_team_logo_label.text = away_abbrev
    
    # Update period/status in top center
    game_period_label.text = status_text
    game_period_label.color = status_color
    
    # Update score in bottom center (X - Y format)
    game_score_label.text = f"{home_score} - {away_score}"
    
    # Update Board 4: Prepare performers for cycling
    top_performers = game.get('top_performers', [])
    current_game_performers = top_performers if top_performers else []
    
    if current_game_performers and len(current_game_performers) > 0:
        # Show first performer initially
        performer = current_game_performers[0]
        name = format_player_name(performer.get('player_name', 'Player'))
        stat_value = performer.get('value', '')
        stat_type = performer.get('stat_category', '')[:3]
        
        # Truncate float values to 1 decimal place
        try:
            if '.' in str(stat_value):
                stat_value = f"{float(stat_value):.1f}"
        except (ValueError, TypeError):
            pass
        
        board4_player_label.text = name
        board4_stat_label.text = f"{stat_value} {stat_type}"
        print(f"Game: {sport_short} {status_text} | {away_abbrev} {away_score} - {home_score} {home_abbrev} | {len(current_game_performers)} performers available")
    else:
        board4_player_label.text = "NO DATA"
        board4_stat_label.text = ""
        print(f"Game: {sport_short} {status_text} | {away_abbrev} {away_score} - {home_score} {home_abbrev} | No performers")


# Initialize
current_game = 0
games = []
next_page_url = None
last_update = 0
last_change = time.monotonic()

# Stats scrolling variables
current_stat_index = 0
last_stat_change = time.monotonic()
STAT_SCROLL_TIME = 3  # seconds to show each stat
current_game_performers = []  # Store current game's performers

# Global label references for efficient updates
sport_label = None
sport_logo_tile = None       # League logo on Board 1
home_team_logo_label = None  # Left side of combined boards 2+3 (text fallback)
home_team_logo_tile = None   # Left side logo bitmap
away_team_logo_label = None  # Right side of combined boards 2+3 (text fallback)
away_team_logo_tile = None   # Right side logo bitmap
team_abbrev_label = None     # Team abbreviations in center
home_rank_label = None       # Small rank indicator for home team
away_rank_label = None       # Small rank indicator for away team
game_period_label = None  # Middle top of combined boards 2+3
game_score_label = None  # Middle bottom of combined boards 2+3
board4_stats_title = None
board4_player_label = None
board4_stat_label = None


def setup_display_layout():
    """Create the display layout once with all labels"""
    global sport_label, sport_logo_tile, home_team_logo_label, game_period_label, home_rank_label, away_rank_label
    global game_score_label, away_team_logo_label, board4_stats_title, board4_player_label, board4_stat_label
    global home_team_logo_tile, away_team_logo_tile, team_abbrev_label
    
    main_group = displayio.Group()
    
    # BOARD 1: League logo (left) + Sport name (right, bold)
    # League logo will be added dynamically based on sport
    # Sport text using smaller font with moderate scale for better size control
    sport_label = label.Label(STATS_FONT, text="", color=TEXT_CYAN, scale=2)
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
    home_team_logo_label = label.Label(STATS_FONT, text="", color=TEXT_WHITE, scale=1)
    home_team_logo_label.anchor_point = (0.0, 0.5)  # Left aligned
    home_team_logo_label.anchored_position = (board_centers[1] - 20, display_height // 2)
    # Note: home_team_logo_label will be added to main_group only if no logo is available
    
    # Right side: Away team (will be logo or text fallback) - positioned towards right side
    away_team_logo_label = label.Label(STATS_FONT, text="", color=TEXT_WHITE, scale=1)
    away_team_logo_label.anchor_point = (1.0, 0.5)  # Right aligned
    away_team_logo_label.anchored_position = (board_centers[2] + 20, display_height // 2)
    # Note: away_team_logo_label will be added to main_group only if no logo is available
    
    # Center: Team abbreviations (HOME vs AWAY)
    team_abbrev_label = label.Label(STATS_FONT, text="", color=TEXT_WHITE, scale=1)
    team_abbrev_label.anchor_point = (0.5, 0.5)
    team_abbrev_label.anchored_position = (combined_center_x, display_height // 2 + 2)
    main_group.append(team_abbrev_label)
    
    # Small rank indicators positioned above team abbreviations
    global home_rank_label, away_rank_label
    home_rank_label = label.Label(SMALLEST_FONT, text="", color=TEXT_CYAN, scale=1)
    home_rank_label.anchor_point = (1.0, 1.0)  # Right-bottom aligned
    home_rank_label.anchored_position = (combined_center_x - 15, display_height // 2 - 1)  # Left of center, above team names
    main_group.append(home_rank_label)
    
    away_rank_label = label.Label(SMALLEST_FONT, text="", color=TEXT_CYAN, scale=1)
    away_rank_label.anchor_point = (0.0, 1.0)  # Left-bottom aligned  
    away_rank_label.anchored_position = (combined_center_x + 15, display_height // 2 - 1)  # Right of center, above team names
    main_group.append(away_rank_label)
    
    # Top: Period/time remaining or status
    game_period_label = label.Label(STATS_FONT, text="", color=TEXT_WHITE, scale=1)
    game_period_label.anchor_point = (0.5, 0.0)
    game_period_label.anchored_position = (combined_center_x, 2)
    main_group.append(game_period_label)
    
    # Bottom: Score (X - Y format)
    game_score_label = label.Label(FONT, text="", color=TEXT_YELLOW, scale=1)
    game_score_label.anchor_point = (0.5, 1.0)
    game_score_label.anchored_position = (combined_center_x, display_height)
    main_group.append(game_score_label)
    
    # BOARD 4: Stats (unchanged)
    board4_stats_title = label.Label(STATS_FONT, text="STATS", color=TEXT_CYAN, scale=1)
    board4_stats_title.anchor_point = (0.5, 0.0)
    board4_stats_title.anchored_position = (board_centers[3], 2)
    main_group.append(board4_stats_title)
    
    board4_player_label = label.Label(STATS_FONT, text="", color=TEXT_WHITE, scale=1)
    board4_player_label.anchor_point = (0.5, 0.5)
    board4_player_label.anchored_position = (board_centers[3], 16)
    main_group.append(board4_player_label)
    
    board4_stat_label = label.Label(STATS_FONT, text="", color=TEXT_GREEN, scale=1)
    board4_stat_label.anchor_point = (0.5, 1.0)
    board4_stat_label.anchored_position = (board_centers[3], 30)
    main_group.append(board4_stat_label)
    
    # Set the display once
    display.root_group = main_group
    print("Display layout created with combined boards 2+3")

print("Starting sports display...")

# Create the display layout once
setup_display_layout()

# Main loop
while True:
    current_time = time.monotonic()
    main_group = displayio.Group()

    # Only fetch new data if we've displayed all current games OR it's been too long
    need_new_data = (
        len(games) == 0 or  # No games loaded yet
        (current_game == 0 and current_time - last_change >= DISPLAY_TIME) or  # Cycled through all games
        (current_time - last_update >= UPDATE_INTERVAL * 3)  # Been too long since last update
    )
    
    if need_new_data:
        print("Fetching sports data...")
        
        # Use next_page_url if available, otherwise start from beginning
        url_to_fetch = next_page_url if next_page_url else None
        new_games, new_next_page_url = fetch_sports_data(url_to_fetch)
        
        if new_games:
            games = new_games
            next_page_url = new_next_page_url
            current_game = 0
            last_update = current_time
            # Show the first game immediately when new data loads
            update_game_display(games[current_game])
            last_change = current_time  # Reset the timer
            print(f"Loaded {len(games)} games. Has next pages: {next_page_url is not None}")
        else:
            # If no new games and we have a next_page_url, reset to beginning
            if next_page_url:
                print("No new games, resetting to first page")
                next_page_url = None
    
    # Show next game
    if games and current_time - last_change >= DISPLAY_TIME:
        update_game_display(games[current_game])
        current_game = (current_game + 1) % len(games)
        last_change = current_time
    
    # Handle stats scrolling (independent of game changes)
    if current_time - last_stat_change >= STAT_SCROLL_TIME:
        current_stat_index += 1
        last_stat_change = current_time
        
        # Update Board 4 stat display if we have performers and label references
        if current_game_performers and board4_player_label and board4_stat_label and len(current_game_performers) > 0:
            performer_index = current_stat_index % len(current_game_performers)
            performer = current_game_performers[performer_index]
            
            name = format_player_name(performer.get('player_name', 'Player'))
            stat_value = performer.get('value', '')
            stat_type = performer.get('stat_category', '')[:3]
            
            # Truncate float values to 1 decimal place
            try:
                if '.' in str(stat_value):
                    stat_value = f"{float(stat_value):.1f}"
            except (ValueError, TypeError):
                pass
            
            # Update both labels - only rows 2 and 3 change
            board4_player_label.text = name
            board4_stat_label.text = f"{stat_value} {stat_type}"
            print(f"Updated Board 4 to show stat {performer_index + 1}/{len(current_game_performers)}: {name} - {stat_value} {stat_type}")
    
    time.sleep(0.3)
