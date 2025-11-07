# boot.py - Configure filesystem for setup mode
import supervisor
import storage

print("Boot: Configuring filesystem for writable access...")

try:
    # Disable web workflow which makes filesystem read-only
    supervisor.disable_web_workflow()
    print("Boot: Web workflow disabled")
except Exception as e:
    print(f"Boot: Could not disable web workflow: {e}")

try:
    # Enable filesystem writes
    storage.remount("/", readonly=False)
    print("Boot: Filesystem remounted as writable")
except Exception as e:
    print(f"Boot: Could not remount filesystem: {e}")

print("Boot: Setup complete")