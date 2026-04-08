import asyncio
from bleak import BleakClient

# --- IMPORTANT: Replace with your device's MAC address ---
DEVICE_ADDRESS = "24:5D:FC:00:6D:79"
# -------------------------------------------------------

async def discover_characteristics(device_address):
    print(f"Connecting to {device_address}...")
    async with BleakClient(device_address) as client:
        print(f"Connected! Discovering services...")
        # `client.services` contains all services and their characteristics
        for service in client.services:
            print(f"\n[Service] {service.uuid}")
            for char in service.characteristics:
                # This will print the UUID of each characteristic
                print(f"    [Characteristic] {char.uuid}")

if __name__ == "__main__":
    asyncio.run(discover_characteristics(DEVICE_ADDRESS))