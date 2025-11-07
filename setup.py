# Sports Display Configuration Server
# Provides web interface for WiFi and sports configuration

import wifi
import socketpool
import microcontroller
import time
import os

try:
    from adafruit_httpserver import Server, Request, Response, GET, POST
    HTTPSERVER_AVAILABLE = True
except ImportError:
    print("adafruit_httpserver not available - using simple socket server")
    HTTPSERVER_AVAILABLE = False

def read_current_settings():
    """Read existing settings from settings.toml"""
    settings = {
        'wifi_ssid': '',
        'wifi_password': '',
        'conferences': 'big_sky',
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
                elif 'detailed_conferences' in line and '=' in line:
                    settings['conferences'] = line.split('=')[1].strip().strip('"\'')
    except Exception as e:
        print(f"Error reading settings: {e}")
    
    return settings

def save_settings(wifi_ssid, wifi_password, conferences, api_url):
    """Save new settings to settings.toml"""
    try:
        settings_content = f'''# Comments are supported
CIRCUITPY_WIFI_SSID = "{wifi_ssid}"
CIRCUITPY_WIFI_PASSWORD = "{wifi_password}"
CIRCUITPY_WEB_API_PORT = 80
CIRCUITPY_WEB_API_PASSWORD = "passw0rd"
TIMEZONE = "America/Denver"

# Sports API Configuration  
API_BASE_URL = "{api_url}"
DETAILED_CONFERENCES = "{conferences}"
'''
        
        with open('settings.toml', 'w') as f:
            f.write(settings_content)
        
        print("Settings saved successfully!")
        return True
        
    except Exception as e:
        print(f"Error saving settings: {e}")
        print("Try disconnecting USB cable, then reconnect after restart")
        return False

def get_setup_html(current_settings):
    """Generate the setup HTML page"""
    return f'''<!DOCTYPE html>
<html>
<head>
    <title>Sports Display Setup</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }}
        .container {{ max-width: 500px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }}
        h1 {{ color: #333; text-align: center; }}
        input, select {{ width: 100%; padding: 10px; margin: 5px 0; border: 1px solid #ddd; border-radius: 5px; }}
        button {{ width: 100%; padding: 15px; background: #007cba; color: white; border: none; border-radius: 5px; font-size: 16px; }}
        button:hover {{ background: #005a87; }}
        .current {{ font-size: 12px; color: #666; }}
        .section {{ margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏀 Sports Display Setup</h1>
        
        <form method="POST" action="/save">
            <div class="section">
                <h3>WiFi Configuration</h3>
                <div class="current">Current: {current_settings['wifi_ssid'] or 'Not configured'}</div>
                <input type="text" name="wifi_ssid" placeholder="WiFi Network Name (SSID)" value="{current_settings['wifi_ssid']}" required>
                <input type="password" name="wifi_password" placeholder="WiFi Password" value="{current_settings['wifi_password']}" required>
            </div>
            
            <div class="section">
                <h3>Sports Configuration</h3>
                <div class="current">Current: {current_settings['conferences']}</div>
                <select name="conferences">
                    <option value="big_sky" {'selected' if current_settings['conferences'] == 'big_sky' else ''}>Big Sky Conference</option>
                    <option value="big_ten" {'selected' if current_settings['conferences'] == 'big_ten' else ''}>Big Ten</option>
                    <option value="sec" {'selected' if current_settings['conferences'] == 'sec' else ''}>SEC</option>
                    <option value="acc" {'selected' if current_settings['conferences'] == 'acc' else ''}>ACC</option>
                    <option value="big_12" {'selected' if current_settings['conferences'] == 'big_12' else ''}>Big 12</option>
                    <option value="pac_12" {'selected' if current_settings['conferences'] == 'pac_12' else ''}>Pac-12</option>
                </select>
            </div>
            
            <div class="section">
                <h3>API Configuration</h3>
                <input type="url" name="api_url" placeholder="API Base URL" value="{current_settings['api_url']}" required>
            </div>
            
            <button type="submit">Save Settings & Restart</button>
        </form>
        
        <div class="section" style="text-align: center; margin-top: 30px;">
            <small>Connect your device to WiFi, then visit this page to make changes later.</small>
        </div>
    </div>
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

def start_config_server():
    """Start the configuration web server"""
    print("Starting configuration server...")
    
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
    
    # Create socket pool and server
    pool = socketpool.SocketPool(wifi.radio)
    server = Server(pool, debug=True)
    
    # Get current settings
    current_settings = read_current_settings()
    
    @server.route("/", GET)
    def serve_setup_page(request: Request):
        """Serve the main setup page"""
        return Response(request, get_setup_html(current_settings), content_type="text/html")
    
    @server.route("/save", POST)
    def save_configuration(request: Request):
        """Handle form submission"""
        try:
            # Parse form data
            form_data = {}
            if hasattr(request, 'form_data'):
                form_data = request.form_data
            else:
                # Manual parsing if form_data not available
                body = request.body.decode('utf-8')
                for pair in body.split('&'):
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        form_data[key] = value.replace('+', ' ')
            
            wifi_ssid = form_data.get('wifi_ssid', '').strip()
            wifi_password = form_data.get('wifi_password', '').strip()
            conferences = form_data.get('conferences', 'big_sky').strip()
            api_url = form_data.get('api_url', 'http://143.110.202.154:8000/api/live').strip()
            
            print(f"Saving: SSID={wifi_ssid}, Conf={conferences}")
            
            if wifi_ssid and wifi_password:
                if save_settings(wifi_ssid, wifi_password, conferences, api_url):
                    # Schedule restart after a brief delay
                    def restart_later():
                        time.sleep(3)
                        microcontroller.reset()
                    
                    # Note: In a real implementation, you'd want to use asyncio or threading
                    # For now, we'll restart after sending the response
                    response = Response(request, get_success_html(), content_type="text/html")
                    
                    # This is a simple approach - send response then restart
                    print("Configuration saved, restarting in 3 seconds...")
                    time.sleep(3)
                    microcontroller.reset()
                    
                    return response
                else:
                    return Response(request, "Error saving settings!", content_type="text/plain")
            else:
                return Response(request, "WiFi SSID and password required!", content_type="text/plain")
                
        except Exception as e:
            print(f"Error processing form: {e}")
            return Response(request, f"Error: {e}", content_type="text/plain")
    
    # Start the server
    try:
        print("Web server starting...")
        server.serve_forever(str(wifi.radio.ipv4_address_ap))
    except Exception as e:
        print(f"Server error: {e}")
        return False

if __name__ == "__main__":
    start_config_server()