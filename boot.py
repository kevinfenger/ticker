# boot.py - Conditional USB drive disable for MatrixPortal S3
# This allows web workflow to write to filesystem when USB drive is disabled
# Hold UP button during power-on to keep USB drive enabled for development

import storage, usb_cdc
import board, digitalio

try:
    # MatrixPortal S3 has UP, DOWN, and RESET buttons
    # We'll use the UP button as our development mode trigger
    dev_mode_button = None
    button_pin_names = ['UP', 'BUTTON_UP', 'DOWN', 'BUTTON_DOWN', 'BOOT0', 'IO0']
    
    for pin_name in button_pin_names:
        try:
            if hasattr(board, pin_name):
                dev_mode_button = digitalio.DigitalInOut(getattr(board, pin_name))
                dev_mode_button.pull = digitalio.Pull.UP
                print(f"Using {pin_name} as development mode button")
                break
        except Exception as pin_e:
            print(f"Failed to use {pin_name}: {pin_e}")
            continue
    
    # Determine what mode we should be in
    development_mode = False  # Default to web workflow mode
    
    if not dev_mode_button:
        print("No button found - using web workflow mode")
    elif dev_mode_button.value == False:  # Button is pressed (pulled to ground)
        development_mode = True
        print("UP button pressed during boot - DEVELOPMENT MODE")
        print("USB drive will stay enabled for file editing")
    else:  # Button not pressed
        print("UP button not pressed - WEB WORKFLOW MODE") 
        print("USB drive would be disabled for web-based configuration")
    
    # Take action based on mode - LIVE MODE ENABLED!
    if development_mode:
        print("✅ LIVE: Keeping USB drive enabled (development mode)")
        # USB drive stays enabled - no action needed
    else:
        print("🚀 LIVE: Disabling USB drive for web workflow mode")
        storage.disable_usb_drive()
        print("✅ USB drive disabled - web workflow can now write to filesystem")
        
except Exception as e:
    # If there's any error with button detection, default to web workflow mode (USB disabled)
    print(f"❌ Error checking development mode button allowing for usb writes to fix issue: {e}")
    #print("🚀 LIVE: Defaulting to web workflow mode - disabling USB drive")
    #storage.disable_usb_drive()
    #print("✅ USB drive disabled due to error - web workflow can write to filesystem")