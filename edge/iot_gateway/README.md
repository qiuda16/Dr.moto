# IoT Gateway Module

This module aggregates sensor data and handles device connectivity.

## Responsibilities
- **Data Collection**: Collect torque data, vibration, temperature.
- **Protocol Translation**: Convert Modbus/BLE/Zigbee to internal event format.
- **Edge Processing**: Basic filtering and aggregation.

## Events
Emits:
- `sensor_reading`
- `device_status`

## Integration
- Input: Serial/Bluetooth/Network Sensors
- Output: MQTT Broker / BFF
