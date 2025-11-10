# Sports Display Configuration Server
# Provides web interface for WiFi and sports configuration

import wifi
import socketpool
import microcontroller
import time
import os

# Version info (keep in sync with code.py)
VERSION = "1.0.0"
GITHUB_REPO = "kevinfenger/ticker"

try:
    from adafruit_httpserver import Server, Request, Response, GET, POST
    HTTPSERVER_AVAILABLE = True
except ImportError:
    print("adafruit_httpserver not available - using simple socket server")
    HTTPSERVER_AVAILABLE = False

def url_decode(url):
    """Decodes a percent-encoded URL string."""
    # First replace + with spaces (URL form encoding)
    url = url.replace('+', ' ')
    
    l = len(url)
    data = bytearray()
    i = 0
    while i < l:
        if url[i] != '%':
            d = ord(url[i])
            i += 1
        else:
            d = int(url[i+1:i+3], 16)
            i += 3
        data.append(d)
    return data.decode('utf-8')

def read_current_settings():
    """Read existing settings from settings.toml"""
    settings = {
        'wifi_ssid': '',
        'wifi_password': '',
        'collections': 'big_sky',
        'timezone': 'America/Denver',
        'api_url': 'http://143.110.202.154:8000/api/live'
    }
    
    try:
        with open('settings.toml', 'r') as f:
            content = f.read()
            # Simple parsing for key settings
            for line in content.split('\n'): 
                if 'CIRCUITPY_WIFI_SSID' in line and '=' in line:
                    settings['wifi_ssid'] = line.split('=')[1].strip().strip('"\'')
                elif 'CIRCUITPY_WIFI_PASSWORD' in line and '=' in line:
                    settings['wifi_password'] = line.split('=')[1].strip().strip('"\'')
                elif 'COLLECTIONS' in line and '=' in line:
                    collections_value = line.split('=')[1].strip().strip('"\'')
                    settings['collections'] = collections_value
                elif 'TIMEZONE' in line and '=' in line:
                    settings['timezone'] = line.split('=')[1].strip().strip('"\'')
    except Exception as e:
        print(f"Error reading settings: {e}")
    
    return settings

def save_settings(wifi_ssid, wifi_password, collections, timezone, api_url):
    """Save new settings to settings.toml"""
    debug_info = []
    debug_info.append(f"Attempting to save settings...")
    debug_info.append(f"SSID='{wifi_ssid}', Collections='{collections}'")
    
    # Check what USB mode we're in and web workflow status
    try:
        import supervisor
        usb_connected = supervisor.runtime.usb_connected
        serial_connected = supervisor.runtime.serial_connected
        debug_info.append(f"USB connected: {usb_connected}")
        debug_info.append(f"Serial connected: {serial_connected}")
        
        # Check if web workflow is enabled
        try:
            # Read settings.toml directly to check web workflow config
            web_workflow_configured = False
            web_api_port = None
            web_api_password = None
            
            try:
                with open('settings.toml', 'r') as f:
                    settings_content = f.read()
                    for line in settings_content.split('\n'):
                        if 'CIRCUITPY_WEB_API_PORT' in line and '=' in line:
                            web_api_port = line.split('=')[1].strip().strip('"\'')
                        elif 'CIRCUITPY_WEB_API_PASSWORD' in line and '=' in line:
                            web_api_password = line.split('=')[1].strip().strip('"\'')
                    
                    if web_api_port and web_api_password:
                        web_workflow_configured = True
                        
            except Exception as settings_e:
                debug_info.append(f"Could not read settings.toml for web workflow check: {settings_e}")
            
            debug_info.append(f"Web workflow port in settings.toml: {web_api_port}")
            debug_info.append(f"Web workflow password in settings.toml: {'Yes' if web_api_password else 'No'}")
            debug_info.append(f"Web workflow configured: {web_workflow_configured}")
            
        except Exception as wf_e:
            debug_info.append(f"Web workflow check failed: {wf_e}")
            
    except:
        debug_info.append("Could not check USB status")
    
    # Print to serial (if connected) and store for web display
    for msg in debug_info:
        print(f"DEBUG: {msg}")
    
    try:
        # First, let's test if we can write to the filesystem at all
        try:
            test_content = f'filesystem write test at {time.monotonic()}'
            with open('debug_write_test.txt', 'w') as test_file:
                test_file.write(test_content)
            debug_info.append("Filesystem write test passed - filesystem is writable!")
            
            # Verify we can read it back
            with open('debug_write_test.txt', 'r') as test_file:
                read_content = test_file.read()
                debug_info.append(f"Read back: {read_content}")
            
            import os
            os.remove('debug_write_test.txt')
            debug_info.append("Test file cleanup successful")
            
        except Exception as test_e:
            debug_info.append(f"Filesystem write test FAILED: {test_e}")
            debug_info.append(f"Error type: {type(test_e).__name__}")
            
            # Check if this is actually a read-only error
            if isinstance(test_e, OSError):
                errno_val = getattr(test_e, 'errno', None)
                strerror_val = getattr(test_e, 'strerror', 'N/A')
                debug_info.append(f"OSError errno: {errno_val}, strerror: {strerror_val}")
                
                # Check specific errno values
                if errno_val == 30:  # EROFS - Read-only file system
                    debug_info.append("Confirmed EROFS (Read-only file system)")
                elif errno_val == 28:  # ENOSPC - No space left
                    debug_info.append("Confirmed ENOSPC (No space left)")
                elif errno_val == 13:  # EACCES - Permission denied
                    debug_info.append("Confirmed EACCES (Permission denied)")
                else:
                    debug_info.append(f"Unknown errno: {errno_val}")
            
            # Print debug info and return detailed error
            for msg in debug_info:
                print(f"DEBUG: {msg}")
            
            return ("test_failed", debug_info, test_e)
        
        settings_content = f'''# Comments are supported
CIRCUITPY_WIFI_SSID = "{wifi_ssid}"
CIRCUITPY_WIFI_PASSWORD = "{wifi_password}"

# Web Workflow - Enables file writing even when connected via USB
CIRCUITPY_WEB_API_PORT = 80
CIRCUITPY_WEB_API_PASSWORD = "passw0rd"
CIRCUITPY_WEB_INSTANCE_NAME = "SportsDisplay"

# Timezone
TIMEZONE = "{timezone}"

# Sports API Configuration  
API_BASE_URL = "{api_url}"
COLLECTIONS = "{collections}"
'''
        
        debug_info.append(f"Writing {len(settings_content)} characters to settings.toml")
        with open('settings.toml', 'w') as f:
            f.write(settings_content)
        
        debug_info.append("Settings saved successfully!")
        
        # Print all debug info to serial (if connected)
        for msg in debug_info:
            print(f"DEBUG: {msg}")
        
        return True
        
    except OSError as e:
        error_msg = str(e).lower()
        errno_val = getattr(e, 'errno', None)
        strerror_val = getattr(e, 'strerror', 'N/A')
        
        debug_info.append(f"OSError details: errno={errno_val}, strerror='{strerror_val}'")
        debug_info.append(f"Full OSError: {e}")
        debug_info.append(f"Error message contains 'readonly': {'readonly' in error_msg}")
        
        # Print debug info to serial
        for msg in debug_info:
            print(f"DEBUG: {msg}")
        
        if "readonly" in error_msg or "read-only" in error_msg or "permission" in error_msg:
            # Check if we can actually see any signs of computer connection
            try:
                import supervisor
                usb_connected = supervisor.runtime.usb_connected
                serial_connected = supervisor.runtime.serial_connected
                
                if not usb_connected and not serial_connected:
                    return ("filesystem_readonly_not_usb", debug_info, e)
                else:
                    return ("readonly", debug_info, e)
            except:
                return ("readonly", debug_info, e)
        elif "space" in error_msg or "full" in error_msg:
            return ("disk_full", debug_info, e)
        else:
            return ("filesystem_error", debug_info, e)
            
    except Exception as e:
        debug_info.append(f"Unexpected error type: {type(e).__name__}")
        debug_info.append(f"Unexpected error details: {e}")
        
        # Print debug info to serial
        for msg in debug_info:
            print(f"DEBUG: {msg}")
            
        return ("unknown_error", debug_info, e)

def get_setup_html(current_settings):
    """Generate the setup HTML page"""
    
    # Get current collections settings (unified approach)
    current_collections = current_settings.get('collections', '')
    
    # Pre-compute checkbox states (unified approach)
    collections_checked = {
        # Sports
        'nba': 'checked' if 'nba' in current_collections else '',
        'wnba': 'checked' if 'wnba' in current_collections else '',
        'nfl': 'checked' if 'nfl' in current_collections else '',
        'mlb': 'checked' if 'mlb' in current_collections else '',
        'nhl': 'checked' if 'nhl' in current_collections else '',
        'mens_college_basketball': 'checked' if 'mens_college_basketball' in current_collections else '',
        'womens_college_basketball': 'checked' if 'womens_college_basketball' in current_collections else '',
        'fcs': 'checked' if 'fcs' in current_collections else '',
        'cfb': 'checked' if 'cfb' in current_collections else '',
        'college_football': 'checked' if 'college_football' in current_collections else '',
        'college_baseball': 'checked' if 'college_baseball' in current_collections else '',
        'premier_league': 'checked' if 'premier_league' in current_collections else '',
        'mls': 'checked' if 'mls' in current_collections else '',
        'champions_league': 'checked' if 'champions_league' in current_collections else '',
        'tennis_atp': 'checked' if 'tennis_atp' in current_collections else '',
        'tennis_wta': 'checked' if 'tennis_wta' in current_collections else '',
        'golf_pga': 'checked' if 'golf_pga' in current_collections else '',
        # Top 25 Rankings
        'cfb_top_25': 'checked' if 'cfb_top_25' in current_collections else '',
        'mcbb_top_25': 'checked' if 'mcbb_top_25' in current_collections else '',
        # Conferences
        'big_sky': 'checked' if 'big_sky' in current_collections else '',
        'big_12': 'checked' if 'big_12' in current_collections else '',
        'mvfc': 'checked' if 'mvfc' in current_collections else '',
    }
    
    print(f"Collections settings: '{current_collections}'")
    print(f"Collections checked states: {collections_checked}")
    
    return f'''<!DOCTYPE html>
<html>
<head>
    <title>Sports Display Setup</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{ box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; 
            margin: 0; 
            padding: 10px; 
            background: #f0f0f0; 
            line-height: 1.4;
        }}
        .container {{ 
            max-width: 600px; 
            margin: 0 auto; 
            background: white; 
            padding: 15px; 
            border-radius: 12px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{ 
            color: #333; 
            text-align: center; 
            margin: 0 0 20px 0; 
            font-size: 24px;
        }}
        h3 {{ 
            color: #444; 
            margin: 15px 0 10px 0; 
            font-size: 18px;
        }}
        h4 {{ 
            color: #555; 
            margin: 15px 0 8px 0; 
            font-size: 16px;
        }}
        input, select {{ 
            width: 100%; 
            padding: 12px; 
            margin: 8px 0; 
            border: 2px solid #ddd; 
            border-radius: 8px; 
            font-size: 16px;
            -webkit-appearance: none;
        }}
        input:focus, select:focus {{ 
            outline: none; 
            border-color: #007cba; 
            box-shadow: 0 0 0 3px rgba(0,124,186,0.1);
        }}
        button {{ 
            width: 100%; 
            padding: 16px; 
            background: #007cba; 
            color: white; 
            border: none; 
            border-radius: 8px; 
            font-size: 18px; 
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }}
        button:hover {{ background: #005a87; }}
        button:active {{ background: #004a70; }}
        .current {{ 
            font-size: 12px; 
            color: #666; 
            margin-bottom: 5px;
            word-break: break-all;
        }}
        .section {{ 
            margin: 25px 0; 
            border-bottom: 1px solid #eee; 
            padding-bottom: 20px;
        }}
        .section:last-of-type {{ border-bottom: none; }}
        .password-container {{ position: relative; }}
        .toggle-password {{ 
            position: absolute; 
            right: 12px; 
            top: 50%; 
            transform: translateY(-50%); 
            background: none; 
            border: none; 
            color: #666; 
            cursor: pointer; 
            padding: 8px; 
            width: auto; 
            font-size: 16px;
            touch-action: manipulation;
        }}
        .toggle-password:hover {{ color: #333; }}
        
        /* Mobile-specific improvements */
        @media (max-width: 480px) {{
            body {{ padding: 5px; }}
            .container {{ 
                padding: 12px; 
                border-radius: 8px;
                margin: 0 5px;
            }}
            h1 {{ font-size: 20px; }}
            h3 {{ font-size: 16px; }}
            h4 {{ font-size: 14px; }}
            input, select {{ 
                padding: 14px 12px; 
                font-size: 16px; /* Prevents zoom on iOS */
            }}
            .checkbox-grid {{
                grid-template-columns: 1fr !important;
            }}
        }}
        
        /* Checkbox grid for conferences */
        .checkbox-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin: 10px 0;
        }}
        .checkbox-item {{
            display: flex;
            align-items: flex-start;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            background: #fafafa;
            transition: all 0.2s;
            cursor: pointer;
            position: relative;
        }}
        .checkbox-item:hover {{ 
            border-color: #007cba; 
            background: #f0f8ff;
        }}
        .checkbox-item input[type="checkbox"] {{
            margin: 2px 10px 0 0;
            width: 18px;
            height: 18px;
            flex-shrink: 0;
            cursor: pointer;
            z-index: 10;
            position: relative;
            accent-color: #007cba;
            transform: scale(1.1);
        }}
        .checkbox-item input[type="checkbox"]:checked {{
            background-color: #007cba;
        }}
        .checkbox-item input[type="checkbox"]:checked + .checkbox-label {{
            font-weight: 600;
            color: #007cba;
        }}
        .checkbox-label {{
            flex-grow: 1;
            font-size: 14px;
            line-height: 1.3;
        }}
        .checkbox-small {{
            font-size: 11px;
            color: #666;
            margin-top: 2px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>&#9632; Sports Display Setup</h1>
        
        <form method="POST" action="/save">
            <div class="section">
                <h3>WiFi Configuration</h3>
                <div class="current">Current: {current_settings['wifi_ssid'] or 'Not configured'}</div>
                <input type="text" name="wifi_ssid" placeholder="WiFi Network Name (SSID)" value="{current_settings['wifi_ssid']}" required>
                <div class="password-container">
                    <input type="password" id="wifi_password" name="wifi_password" placeholder="WiFi Password" value="{current_settings['wifi_password']}" required>
                    <button type="button" class="toggle-password" onclick="togglePassword()">Show</button>
                </div>
            </div>
            
            <div class="section">
                <h3>&#9733; What Do You Want to Follow?</h3>
                <div class="current">
                    <strong>Currently following:</strong> 
                    <span id="current-selections">Loading selections...</span>
                </div>
                
                <h4>&#8226; Professional Sports:</h4>
                <div class="checkbox-grid">
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="nba" {collections_checked['nba']}>
                        <div class="checkbox-label">
                            [NBA] Basketball
                            <div class="checkbox-small">Professional basketball league</div>
                        </div>
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="wnba" {collections_checked['wnba']}>
                        <div class="checkbox-label">
                            [WNBA] Basketball
                            <div class="checkbox-small">Women's professional basketball</div>
                        </div>
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="nfl" {collections_checked['nfl']}>
                        <div class="checkbox-label">
                            [NFL] Football
                            <div class="checkbox-small">Professional football league</div>
                        </div>
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="mlb" {collections_checked['mlb']}>
                        <div class="checkbox-label">
                            [MLB] Baseball
                            <div class="checkbox-small">Professional baseball league</div>
                        </div>
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="nhl" {collections_checked['nhl']}>
                        <div class="checkbox-label">
                            [NHL] Hockey
                            <div class="checkbox-small">Professional hockey league</div>
                        </div>
                    </label>
                </div>
                    
                <h4>&#8226; College Sports:</h4>
                <div class="checkbox-grid">
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="mens_college_basketball" {collections_checked['mens_college_basketball']}>
                        <div class="checkbox-label">
                            [College] Basketball (Men)
                            <div class="checkbox-small">Featured mens college basketball games</div>
                        </div>
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="womens_college_basketball" {collections_checked['womens_college_basketball']}>
                        <div class="checkbox-label">
                            [College] Basketball (Womens)
                            <div class="checkbox-small">Featured womens college basketball games</div>
                        </div>
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="college_football" {collections_checked['college_football']}>
                        <div class="checkbox-label">
                            [College] All College Football (FBS + FCS)
                            <div class="checkbox-small">All college football - large</div>
                        </div>
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="cfb" {collections_checked['cfb']}>
                        <div class="checkbox-label">
                            [College] College Football Smaller Subset
                            <div class="checkbox-small">All college football - small</div>
                        </div>
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="fcs" {collections_checked['fcs']}>
                        <div class="checkbox-label">
                            [College] FCS College Football
                            <div class="checkbox-small">just FCS football</div>
                        </div>
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="college_baseball" {collections_checked['college_baseball']}>
                        <div class="checkbox-label">
                            [College] Baseball
                            <div class="checkbox-small">Featured college baseball games</div>
                        </div>
                    </label>
                </div>
                    
                <h4>&#8226; Top 25 Rankings:</h4>
                <div class="checkbox-grid">
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="cfb_top_25" {collections_checked['cfb_top_25']}>
                        <div class="checkbox-label">
                            [Top 25] College Football
                            <div class="checkbox-small">Top 25 ranked college football teams</div>
                        </div>
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="mcbb_top_25" {collections_checked['mcbb_top_25']}>
                        <div class="checkbox-label">
                            [Top 25] Men's College Basketball
                            <div class="checkbox-small">Top 25 ranked mens college basketball teams</div>
                        </div>
                    </label>
                </div>
                    
                <h4>&#8226; International Sports:</h4>
                <div class="checkbox-grid">
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="premier_league" {collections_checked['premier_league']}>
                        <div class="checkbox-label">
                            [Soccer] Premier League
                            <div class="checkbox-small">English football</div>
                        </div>
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="mls" {collections_checked['mls']}>
                        <div class="checkbox-label">
                            [Soccer] MLS
                            <div class="checkbox-small">Major League Soccer</div>
                        </div>
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="champions_league" {collections_checked['champions_league']}>
                        <div class="checkbox-label">
                            [Soccer] Champions League
                            <div class="checkbox-small">European tournament</div>
                        </div>
                    </label>
                </div>
                <!-- TODO TEMPORARILY DISABLED - No handling for individual leaderboards on the frontend -->
                <!--    
                <h4>&#8226; Individual Sports:</h4>
                <div class="checkbox-grid">
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="tennis_atp" {collections_checked['tennis_atp']}>
                        <div class="checkbox-label">
                            [Tennis] ATP
                            <div class="checkbox-small">Men's professional tennis</div>
                        </div>
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="tennis_wta" {collections_checked['tennis_wta']}>
                        <div class="checkbox-label">
                            [Tennis] WTA
                            <div class="checkbox-small">Women's professional tennis</div>
                        </div>
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="golf_pga" {collections_checked['golf_pga']}>
                        <div class="checkbox-label">
                            [Golf] PGA
                            <div class="checkbox-small">Professional golf tour</div>
                        </div>
                    </label>
                </div>
                -->

                <h4>&#8226; Conferences:</h4>
                <div class="checkbox-grid">
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="big_sky" {collections_checked['big_sky']}>
                        <div class="checkbox-label">
                            Big Sky Conference
                            <div class="checkbox-small">Basketball: Group 5, Football: Group 20</div>
                        </div>
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="big_12" {collections_checked['big_12']}>
                        <div class="checkbox-label">
                            Big 12
                            <div class="checkbox-small">Basketball: Group 21</div>
                        </div>
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" name="collections" value="mvfc" {collections_checked['mvfc']}>
                        <div class="checkbox-label">
                            MVFC/Missouri Valley
                            <div class="checkbox-small">Football: Group 21</div>
                        </div>
                    </label>
                </div>
            </div>
            
            <div class="section">
                <h3>Timezone Configuration</h3>
                <div class="current">Current: {current_settings.get('timezone', 'America/Denver')}</div>
                <select name="timezone">
                    <optgroup label="US Timezones">
                        <option value="America/New_York" {'selected' if current_settings.get('timezone') == 'America/New_York' else ''}>Eastern Time (New York)</option>
                        <option value="America/Chicago" {'selected' if current_settings.get('timezone') == 'America/Chicago' else ''}>Central Time (Chicago)</option>
                        <option value="America/Denver" {'selected' if current_settings.get('timezone') == 'America/Denver' else ''}>Mountain Time (Denver)</option>
                        <option value="America/Phoenix" {'selected' if current_settings.get('timezone') == 'America/Phoenix' else ''}>Arizona Time (Phoenix)</option>
                        <option value="America/Los_Angeles" {'selected' if current_settings.get('timezone') == 'America/Los_Angeles' else ''}>Pacific Time (Los Angeles)</option>
                        <option value="America/Anchorage" {'selected' if current_settings.get('timezone') == 'America/Anchorage' else ''}>Alaska Time (Anchorage)</option>
                        <option value="Pacific/Honolulu" {'selected' if current_settings.get('timezone') == 'Pacific/Honolulu' else ''}>Hawaii Time (Honolulu)</option>
                    </optgroup>
                    <optgroup label="Canada">
                        <option value="America/Toronto" {'selected' if current_settings.get('timezone') == 'America/Toronto' else ''}>Eastern Time (Toronto)</option>
                        <option value="America/Winnipeg" {'selected' if current_settings.get('timezone') == 'America/Winnipeg' else ''}>Central Time (Winnipeg)</option>
                        <option value="America/Edmonton" {'selected' if current_settings.get('timezone') == 'America/Edmonton' else ''}>Mountain Time (Edmonton)</option>
                        <option value="America/Vancouver" {'selected' if current_settings.get('timezone') == 'America/Vancouver' else ''}>Pacific Time (Vancouver)</option>
                    </optgroup>
                    <optgroup label="Europe">
                        <option value="Europe/London" {'selected' if current_settings.get('timezone') == 'Europe/London' else ''}>GMT (London)</option>
                        <option value="Europe/Paris" {'selected' if current_settings.get('timezone') == 'Europe/Paris' else ''}>CET (Paris)</option>
                        <option value="Europe/Berlin" {'selected' if current_settings.get('timezone') == 'Europe/Berlin' else ''}>CET (Berlin)</option>
                        <option value="Europe/Rome" {'selected' if current_settings.get('timezone') == 'Europe/Rome' else ''}>CET (Rome)</option>
                    </optgroup>
                    <optgroup label="Other">
                        <option value="UTC" {'selected' if current_settings.get('timezone') == 'UTC' else ''}>UTC (Coordinated Universal Time)</option>
                    </optgroup>
                </select>
            </div>
            
            <div class="section">
                <div class="advanced-toggle" onclick="toggleAdvanced()">
                    <h3 style="margin: 0; display: flex; align-items: center; cursor: pointer; user-select: none;">
                        <span id="advanced-icon" style="margin-right: 8px; font-size: 18px; transition: transform 0.2s;">+</span>
                        Advanced Settings
                    </h3>
                </div>
                
                <div id="advanced-content" style="display: none; margin-top: 15px;">
                    <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #f39c12;">
                        <h4 style="color: #856404; margin: 0 0 8px 0; font-size: 14px;">Warning</h4>
                        <p style="color: #856404; margin: 0; font-size: 13px; line-height: 1.4;">
                            These are advanced settings. Changing the API URL could result in incomplete or no sports data. 
                            Only modify these settings if you know what you're doing or have been instructed to do so.
                        </p>
                    </div>
                    
                    <h4>API Configuration</h4>
                    <input type="url" name="api_url" placeholder="API Base URL" value="{current_settings['api_url']}" required>
                </div>
            </div>
            
            <button type="submit">Save Settings & Restart</button>
        </form>
        
                <div class="section" style="text-align: center; margin-top: 15px;">
            <div style="background: #e3f2fd; padding: 12px; border-radius: 6px; margin: 10px 0; font-size: 13px;">
                <strong>Pro Tip</strong><br>
                <span style="color: #1976d2;">After startup, this URL will be displayed on your LED matrix for easy access!</span>
            </div>
        </div>
        
        <div class="section" style="margin-top: 20px;">
            <h4 style="margin-bottom: 10px; color: #333;">Device Information</h4>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 4px solid #28a745;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span><strong>Current Version:</strong></span>
                    <code style="background: #e9ecef; padding: 2px 6px; border-radius: 3px;">v{VERSION}</code>
                </div>
                <!-- TODO TEMPORARILY DISABLED - Update functionality hidden until implementation decided -->
                <!--
                <div style="margin-bottom: 10px;">
                    <button type="button" id="checkUpdatesBtn" onclick="checkForUpdates()" 
                            style="background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">
                        Check for Updates
                    </button>
                </div>
                <div id="updateStatus" style="margin-top: 10px; font-size: 13px;"></div>
                -->
            </div>
        </div>
    </div>
    
    <script>
        function togglePassword() {{
            const passwordField = document.getElementById('wifi_password');
            const toggleButton = document.querySelector('.toggle-password');
            
            if (passwordField.type === 'password') {{
                passwordField.type = 'text';
                toggleButton.textContent = 'Hide';
            }} else {{
                passwordField.type = 'password';
                toggleButton.textContent = 'Show';
            }}
        }}

        function toggleAdvanced() {{
            const content = document.getElementById('advanced-content');
            const icon = document.getElementById('advanced-icon');
            
            if (content.style.display === 'none') {{
                content.style.display = 'block';
                icon.textContent = '-';
                icon.style.transform = 'rotate(0deg)';
            }} else {{
                content.style.display = 'none';
                icon.textContent = '+';
                icon.style.transform = 'rotate(0deg)';
            }}
        }}

        function checkForUpdates() {{
            const btn = document.getElementById('checkUpdatesBtn');
            const status = document.getElementById('updateStatus');
            
            btn.disabled = true;
            btn.textContent = 'Checking...';
            status.innerHTML = '<span style="color: #6c757d;">Checking GitHub for updates...</span>';
            
            fetch('/check-updates')
                .then(response => response.json())
                .then(data => {{
                    if (data.available) {{
                        status.innerHTML = `
                            <div style="color: #28a745; margin-bottom: 8px;">
                                <strong>✓ Update Available: v${{data.version}}</strong>
                            </div>
                            <div style="font-size: 12px; color: #6c757d; margin-bottom: 8px;">
                                Released: ${{data.published}}
                            </div>
                            <button onclick="installUpdate('${{data.version}}')" 
                                    style="background: #28a745; color: white; border: none; padding: 6px 12px; border-radius: 3px; cursor: pointer; font-size: 12px;">
                                Install Update
                            </button>
                        `;
                    }} else if (data.error) {{
                        status.innerHTML = `<span style="color: #dc3545;">Error: ${{data.error}}</span>`;
                    }} else {{
                        status.innerHTML = `<span style="color: #28a745;">✓ Running latest version (${{data.current}})</span>`;
                    }}
                }})
                .catch(err => {{
                    status.innerHTML = `<span style="color: #dc3545;">Error checking for updates: ${{err.message}}</span>`;
                }})
                .finally(() => {{
                    btn.disabled = false;
                    btn.textContent = 'Check for Updates';
                }});
        }}
        
        function installUpdate(version) {{
            if (!confirm(`Install update v${{version}}? This will restart the device.`)) {{
                return;
            }}
            
            const status = document.getElementById('updateStatus');
            status.innerHTML = '<span style="color: #007bff;">Installing update... Device will restart automatically.</span>';
            
            fetch('/install-update', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{version: version}})
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    status.innerHTML = '<span style="color: #28a745;">Update installed successfully. Restarting...</span>';
                }} else {{
                    status.innerHTML = `<span style="color: #dc3545;">Update failed: ${{data.error}}</span>`;
                }}
            }})
            .catch(err => {{
                status.innerHTML = `<span style="color: #dc3545;">Update failed: ${{err.message}}</span>`;
            }});
        }}

        function updateCurrentSelections() {{
            const allSelected = [];

            // Get all selected collections
            const collectionCheckboxes = document.querySelectorAll('input[name="collections"]:checked');
            collectionCheckboxes.forEach(checkbox => {{
                const label = checkbox.closest('.checkbox-item').querySelector('.checkbox-label');
                const collectionName = label.firstChild.textContent.trim();
                allSelected.push(collectionName);
            }});

            // Update display
            const currentDisplay = document.getElementById('current-selections');
            let displayText = '';
            
            if (allSelected.length > 0) {{
                displayText = allSelected.join(', ');
            }} else {{
                displayText = 'Nothing selected';
            }}
            
            currentDisplay.textContent = displayText;
            
            // Update styling based on selections
            if (allSelected.length > 0) {{
                currentDisplay.style.color = '#007cba';
                currentDisplay.style.fontWeight = '600';
            }} else {{
                currentDisplay.style.color = '#666';
                currentDisplay.style.fontWeight = 'normal';
            }}
        }}

        // Add event listeners when page loads
        document.addEventListener('DOMContentLoaded', function() {{
            // Update display on page load
            updateCurrentSelections();
            
            // Add change listeners to all checkboxes
            const allCheckboxes = document.querySelectorAll('input[name="collections"]');
            allCheckboxes.forEach(checkbox => {{
                checkbox.addEventListener('change', updateCurrentSelections);
            }});
        }});
    </script>
</body>
</html>'''

def get_success_html():
    """Generate success page"""
    return '''<!DOCTYPE html>
<html>
<head>
    <title>Setup Complete</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="5;url=/">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; text-align: center; }
        .container { max-width: 500px; margin: 50px auto; background: white; padding: 20px; border-radius: 10px; }
        h1 { color: #28a745; }
    </style>
</head>
<body>
    <div class="container">
        <h1>✓ Setup Complete!</h1>
        <p>Your settings have been saved.</p>
        <p>The device will restart in a few seconds to apply the new WiFi configuration.</p>
        <p>Once connected, the sports display will begin automatically.</p>
    </div>
</body>
</html>'''

def start_config_server(setup_mode=True, pool=None):
    """Start the configuration web server
    
    Args:
        setup_mode: If True, creates AP and runs blocking server (initial setup)
                   If False, uses existing WiFi and returns server for polling
        pool: Socket pool to use (required when setup_mode=False)
    """
    if setup_mode:
        print("Starting configuration server in setup mode...")
        # Create Access Point
        try:
            wifi.radio.start_ap("SportsDisplay-Setup", "sports123")
            print("Access Point created: SportsDisplay-Setup")
            print("Password: sports123")
            print(f"Connect and visit: http://{wifi.radio.ipv4_address_ap}")
        except Exception as e:
            print(f"Failed to start AP: {e}")
            return False
        
        if not HTTPSERVER_AVAILABLE:
            print("HTTP server library not available!")
            return False
        
        # Create socket pool and server for AP mode
        pool = socketpool.SocketPool(wifi.radio)
    else:
        print("Starting configuration server in background mode...")
        if not pool:
            print("Socket pool required for background mode!")
            return None
        
        if not HTTPSERVER_AVAILABLE:
            print("HTTP server library not available!")
            return None
    
    # Create server
    server = Server(pool, debug=(setup_mode))
    
    # Get current settings
    current_settings = read_current_settings()
    
    @server.route("/", GET)
    def serve_setup_page(request: Request):
        """Serve the main setup page"""
        print(f"HTTP GET request received for / from {request.client_address if hasattr(request, 'client_address') else 'unknown'}")
        print(f"Request path: {request.path}")
        print(f"Request method: {request.method}")
        # Always read fresh settings to show current state
        fresh_settings = read_current_settings()
        return Response(request, get_setup_html(fresh_settings), content_type="text/html")
    
    @server.route("/save", POST)
    def save_configuration(request: Request):
        """Handle form submission"""
        try:
            # Parse form data - always use manual parsing to ensure URL decoding
            form_data = {}
            # Always use manual parsing to ensure proper URL decoding
            body = request.body.decode('utf-8')
            for pair in body.split('&'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    # Handle multiple values for same key (checkboxes)
                    # URL decode the value using our custom function
                    decoded_value = url_decode(value)
                    
                    if key in form_data:
                        if isinstance(form_data[key], list):
                            form_data[key].append(decoded_value)
                        else:
                            form_data[key] = [form_data[key], decoded_value]
                    else:
                        form_data[key] = decoded_value
            
            wifi_ssid = form_data.get('wifi_ssid', '').strip()
            wifi_password = form_data.get('wifi_password', '').strip()
            
            # Handle multiple collections selections
            collections_raw = form_data.get('collections', [])
            
            if isinstance(collections_raw, list):
                collections = ','.join(collections_raw)
            elif collections_raw and collections_raw.strip():
                collections = collections_raw.strip()
            else:
                # Default if nothing selected
                collections = 'basketball_mens-college,big_sky'
            
            timezone = form_data.get('timezone', 'America/Denver').strip()
            api_url = form_data.get('api_url', 'http://143.110.202.154:8000/api/live').strip()
            
            print(f"Saving: SSID={wifi_ssid}, Collections={collections}, TZ={timezone}")
            
            if wifi_ssid and wifi_password:
                save_result = save_settings(wifi_ssid, wifi_password, collections, timezone, api_url)
                
                # Handle both old format (True/False/string) and new format (tuple with debug info)
                if save_result == True:
                    if setup_mode:
                        # In setup mode, restart immediately after showing success page
                        response = Response(request, get_success_html(), content_type="text/html")
                        print("Configuration saved, restarting in 3 seconds...")
                        time.sleep(3)
                        microcontroller.reset()
                        return response
                    else:
                        # In background mode, just restart after brief delay
                        response_html = '''<!DOCTYPE html>
<html><head><title>Settings Updated</title><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="font-family: Arial; text-align: center; padding: 50px; background: #f0f0f0;">
<div style="max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px;">
<h1 style="color: #28a745;">✓ Settings Updated!</h1>
<p>Configuration saved successfully.</p>
<p>Device will restart in 3 seconds to apply changes...</p>
</div></body></html>'''
                        
                        print("Background config saved, restarting in 3 seconds...")
                        time.sleep(3)
                        microcontroller.reset()
                        return Response(request, response_html, content_type="text/html")
                        
                elif isinstance(save_result, tuple) and save_result[0] == "test_failed":
                    # Filesystem test failed - show debug info
                    error_type, debug_info, error_obj = save_result
                    debug_html = '<br>'.join(debug_info)
                    test_failed_html = f'''<!DOCTYPE html>
<html><head><title>Filesystem Test Failed</title><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="font-family: Arial; padding: 20px; background: #f0f0f0;">
<div style="max-width: 700px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; border: 3px solid #f44336;">
<h1 style="color: #d32f2f;">Filesystem Test Failed</h1>
<p style="font-size: 16px;">Cannot write to filesystem. Here's what we found:</p>

<div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0; font-family: monospace; font-size: 13px; white-space: pre-wrap;">{debug_html}</div>

<div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0;">
<h3 style="color: #856404; margin-top: 0;">Next Steps:</h3>
<ul style="color: #856404;">
<li><strong>If you see "Read-only file system":</strong> Try disconnecting from computer</li>
<li><strong>If you see "No space left":</strong> Delete some files from the device</li>
<li><strong>If you see other errors:</strong> Try restarting the device</li>
</ul>
</div>

<button onclick="location.reload()" style="background: #007cba; color: white; border: none; padding: 12px 24px; border-radius: 6px; font-size: 16px; cursor: pointer;">Try Again</button>
</div></body></html>'''
                    return Response(request, test_failed_html, content_type="text/html")
                    
                elif save_result == "filesystem_readonly_not_usb" or (isinstance(save_result, tuple) and save_result[0] == "filesystem_readonly_not_usb"):
                    # Filesystem is read-only but not due to USB connection
                    mystery_readonly_html = '''<!DOCTYPE html>
<html><head><title>Mysterious Read-Only Error</title><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="font-family: Arial; text-align: center; padding: 20px; background: #f0f0f0;">
<div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; border: 3px solid #ff9800;">
<h1 style="color: #f57c00;">Mysterious Read-Only Issue</h1>
<p style="font-size: 16px; margin: 20px 0;"><strong>Filesystem is read-only, but no USB data connection detected.</strong></p>

<div style="background: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: left;">
<h3 style="color: #ef6c00; margin-top: 0;">Possible Causes:</h3>
<ul style="color: #ef6c00; line-height: 1.6;">
<li>Device filesystem corruption</li>
<li>Power supply issue causing instability</li>
<li>Device needs full restart/reset</li>
<li>Hardware problem with flash memory</li>
</ul>
</div>

<div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: left;">
<h3 style="color: #1976d2; margin-top: 0;">Try These Solutions:</h3>
<ol style="color: #1976d2; line-height: 1.6;">
<li><strong>Restart the device completely</strong> (power cycle)</li>
<li><strong>Check power supply</strong> - use a different wall charger</li>
<li><strong>Try connecting briefly to computer</strong> to check filesystem</li>
<li><strong>Check serial console</strong> for detailed error info</li>
</ol>
</div>

<p style="color: #666; font-size: 14px;">Check the serial monitor for detailed debugging information.</p>
<button onclick="location.reload()" style="background: #007cba; color: white; border: none; padding: 12px 24px; border-radius: 6px; font-size: 16px; cursor: pointer; margin-top: 15px;">
↻ Try Again
</button>
</div></body></html>'''
                    return Response(request, mystery_readonly_html, content_type="text/html")
                    
                elif save_result == "readonly" or (isinstance(save_result, tuple) and save_result[0] == "readonly"):
                    # Special handling for read-only filesystem
                    readonly_html = '''<!DOCTYPE html>
<html><head><title>USB Data Connection Issue</title><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="font-family: Arial; text-align: center; padding: 20px; background: #f0f0f0;">
<div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; border: 3px solid #ff6b35;">
<h1 style="color: #d32f2f;">USB Data Connection Detected</h1>
<p style="font-size: 16px; margin: 20px 0;"><strong>Cannot save settings while connected to a computer via USB data cable.</strong></p>

<div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: left;">
<h3 style="color: #856404; margin-top: 0;">Quick Fix (if debugging):</h3>
<ol style="color: #856404; line-height: 1.6;">
<li><strong>Disconnect the USB cable</strong> from computer</li>
<li><strong>Wait 2-3 seconds</strong> for filesystem to unlock</li>
<li><strong>Reconnect the USB cable</strong></li>
<li><strong>Try saving again</strong></li>
</ol>
</div>

<div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: left;">
<h3 style="color: #2e7d32; margin-top: 0;">Better Solution (for normal use):</h3>
<p style="color: #2e7d32; margin: 5px 0;"><strong>Use a power-only connection:</strong></p>
<ul style="color: #2e7d32; line-height: 1.6; margin: 10px 0;">
<li>Wall charger/USB power adapter</li>
<li>Portable battery pack</li>
<li>Car USB charger (power-only ports)</li>
</ul>
<p style="color: #2e7d32; margin: 5px 0;"><strong>→ Settings will save without any disconnection needed!</strong></p>
</div>

<div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: left;">
<p style="color: #1976d2; margin: 0; font-size: 14px;"><strong>Why this happens:</strong> When connected to a computer, CircuitPython makes the filesystem read-only to prevent conflicts. Power-only connections (wall chargers, etc.) don't have this restriction because there's no data connection.</p>
</div>

<button onclick="location.reload()" style="background: #007cba; color: white; border: none; padding: 12px 24px; border-radius: 6px; font-size: 16px; cursor: pointer; margin-top: 15px;">
↻ Try Again After Disconnecting
</button>
</div></body></html>'''
                    return Response(request, readonly_html, content_type="text/html")
                    
                elif save_result == "disk_full":
                    disk_full_html = '''<!DOCTYPE html>
<html><head><title>Disk Full</title><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="font-family: Arial; text-align: center; padding: 20px; background: #f0f0f0;">
<div style="max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; border: 3px solid #f44336;">
<h1 style="color: #d32f2f;">💾 Disk Full</h1>
<p>Not enough space on device to save settings.</p>
<p>Try removing some files from the CIRCUITPY drive and try again.</p>
<button onclick="location.reload()" style="background: #007cba; color: white; border: none; padding: 12px 24px; border-radius: 6px; font-size: 16px; cursor: pointer; margin-top: 15px;">Try Again</button>
</div></body></html>'''
                    return Response(request, disk_full_html, content_type="text/html")
                    
                elif save_result == "filesystem_error":
                    fs_error_html = '''<!DOCTYPE html>
<html><head><title>Filesystem Error</title><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="font-family: Arial; text-align: center; padding: 20px; background: #f0f0f0;">
<div style="max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; border: 3px solid #f44336;">
<h1 style="color: #d32f2f;">Filesystem Error</h1>
<p>Unable to write to device filesystem.</p>
<p>Check the serial console for detailed error information.</p>
<p>Try restarting the device and trying again.</p>
<button onclick="location.reload()" style="background: #007cba; color: white; border: none; padding: 12px 24px; border-radius: 6px; font-size: 16px; cursor: pointer; margin-top: 15px;">Try Again</button>
</div></body></html>'''
                    return Response(request, fs_error_html, content_type="text/html")
                    
                else:
                    # Generic error with debug info
                    generic_error_html = f'''<!DOCTYPE html>
<html><head><title>Save Error</title><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="font-family: Arial; text-align: center; padding: 20px; background: #f0f0f0;">
<div style="max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; border: 3px solid #f44336;">
<h1 style="color: #d32f2f;">Save Error</h1>
<p>Error saving settings: {save_result}</p>
<p>Check the serial console for detailed error information.</p>
<button onclick="location.reload()" style="background: #007cba; color: white; border: none; padding: 12px 24px; border-radius: 6px; font-size: 16px; cursor: pointer; margin-top: 15px;">Try Again</button>
</div></body></html>'''
                    return Response(request, generic_error_html, content_type="text/html")
            else:
                return Response(request, "WiFi SSID and password required!", content_type="text/plain")
                
        except Exception as e:
            print(f"Error processing form: {e}")
            return Response(request, f"Error: {e}", content_type="text/plain")
    
    @server.route("/check-updates", GET)
    def check_updates_endpoint(request: Request):
        """API endpoint to check for GitHub updates"""
        try:
            # Import the update function from code.py
            import code
            update_info = code.check_github_releases()
            
            # Return JSON response
            import json
            return Response(request, json.dumps(update_info), content_type="application/json")
            
        except Exception as e:
            print(f"Error checking updates: {e}")
            error_response = {{'error': str(e)}}
            import json
            return Response(request, json.dumps(error_response), content_type="application/json")
    
    @server.route("/install-update", POST)
    def install_update_endpoint(request: Request):
        """API endpoint to install updates (placeholder for now)"""
        try:
            import json
            
            # For now, just return that the feature is not implemented yet
            response = {{
                'success': False,
                'error': 'Update installation will be implemented in the next phase'
            }}
            
            return Response(request, json.dumps(response), content_type="application/json")
            
        except Exception as e:
            print(f"Error in update installation: {e}")
            error_response = {{'success': False, 'error': str(e)}}
            import json
            return Response(request, json.dumps(error_response), content_type="application/json")
    
    # Start the server based on mode
    if setup_mode:
        # Blocking server for initial setup
        try:
            print("Web server starting...")
            server.serve_forever(str(wifi.radio.ipv4_address_ap))
        except Exception as e:
            print(f"Server error: {e}")
            return False
    else:
        # Return server for polling in background mode
        try:
            print(f"Starting background server on {wifi.radio.ipv4_address}:5000")
            server.start(str(wifi.radio.ipv4_address), port=5000)
            print("Background configuration server started successfully")
            return server
        except Exception as e:
            print(f"Failed to start background server: {e}")
            return None



if __name__ == "__main__":
    start_config_server()