import bluetooth

def setup_bluetooth():
    global bt_client_sock
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    server_sock.bind(("", bluetooth.PORT_ANY))
    server_sock.listen(1)

    port = server_sock.getsockname()[1]
    bluetooth.advertise_service(
        server_sock, 
        "FishMonitor",
        service_classes=[bluetooth.SERIAL_PORT_CLASS],
        profiles=[bluetooth.SERIAL_PORT_PROFILE]
    )
    print(f"Waiting for Bluetooth connection on RFCOMM channel {port}...")
    print("[BT] Open MIT App Inventor app and connect to 'FishMonitor'")

    try:
        bt_client_sock, client_info = server_sock.accept()
        print(f"Bluetooth connected: {client_info}")
    except Exception as e:
        print(f"Bluetooth connection failed: {e}")
        bt_client_sock = None
        
def build_bt_message(temperature, tds_ppm, water_percent,
                     fish_count, counting_mode,
                     relay_heater, relay_pump, relay_valve):
    heater = "ON" if relay_heater else "OFF"
    pump   = "ON" if relay_pump   else "OFF"
    valve  = "ON" if relay_valve  else "OFF"
    mode   = "COUNTING" if counting_mode else "IDLE"
    message = (
        f"TEMP:{temperature:.1f},"
        f"TDS:{tds_ppm:.0f},"
        f"WATER:{water_percent:.0f},"
        f"FISH:{fish_count},"
        f"HEATER:{heater},"
        f"PUMP:{pump},"
        f"VALVE:{valve},"
        f"MODE:{mode}\n"
    )
    return message

def send_bluetooth_data(temperature, tds_ppm, water_percent,
                        fish_count, counting_mode,
                        relay_heater, relay_pump, relay_valve):
    
    message = build_bt_message(temperature, tds_ppm, water_percent,
                               fish_count, counting_mode,
                               relay_heater, relay_pump, relay_valve)
    
    if bt_client_sock is None:
        print("[BT] No phone connected — skipping send")
        return

    try:
        bt_client_sock.send(message.encode("utf-8"))
    except bluetooth.BluetoothError as e:
        print(f"[BT] Phone disconnected: {e}")
        bt_client_sock = None  # reset so next reconnect attempt works
    except Exception as e:
        print(f"[BT] Send error: {e}")