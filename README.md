# ArduSub PyMavlink Control Extension

A BlueOS extension that provides a web-based interface for controlling ArduSub vehicles using PyMavlink. This extension allows users to control vehicle movement, set target depth and heading, and manage vehicle modes through an intuitive Vue.js frontend.

## Features

- **Vehicle Connection Management**: Connect to ArduSub vehicles via MAVLink
- **Heartbeat Detection**: Automatic detection of vehicle heartbeat for connection validation
- **Vehicle Control**: Arm/disarm vehicle and set flight modes (e.g., ALT_HOLD)
- **Depth Control**: Set target depth with "Go!" button
- **Heading Control**: Set target heading with "Go!" button
- **Movement Control**: Four directional movement buttons (up, down, left, right) with configurable throttle and duration
- **Real-time Status**: Live vehicle status monitoring including connection, heartbeat, armed state, and mode
- **Message Logging**: Comprehensive logging of all operations and errors
- **Modern UI**: Beautiful, responsive Vue.js frontend with intuitive controls

## Architecture

- **Backend**: Flask server with PyMavlink integration
- **Frontend**: Vue.js 3 with modern CSS styling
- **Communication**: RESTful API endpoints for vehicle control
- **MAVLink**: Direct communication with ArduSub vehicles using PyMavlink

## Prerequisites

- BlueOS running on your vehicle
- ArduSub firmware on your vehicle
- Vehicle powered on and accessible via MAVLink

## Installation

### Building the Docker Image

1. Clone this repository:
```bash
git clone <repository-url>
cd ArduSub_PyMavlinkDemo
```

2. Build the Docker image:
```bash
docker build -t ardusub-pymavlink-control .
```

3. Push to Docker Hub (optional):
```bash
docker tag ardusub-pymavlink-control <your-dockerhub-username>/ardusub-pymavlink-control
docker push <your-dockerhub-username>/ardusub-pymavlink-control
```

### Deploying to BlueOS

1. In BlueOS, go to the Extensions page
2. Click "Add Extension"
3. Enter the Docker image name: `ardusub-pymavlink-control` (or your Docker Hub image)
4. Click "Submit"
5. The extension will be deployed and accessible via the BlueOS interface

## Usage

### Initial Setup

1. **Connect**: Click the "Connect" button to initiate connection to the vehicle
2. **Wait for Heartbeat**: Click "Wait for Heartbeat" to establish communication
3. **Set Mode**: Click "Set Alt-Hold Mode" to put the vehicle in altitude hold mode
4. **Arm Vehicle**: Click "Arm Vehicle" to arm the vehicle (when ready)

### Vehicle Control

#### Depth Control
- Enter target depth in meters (0-100)
- Click "Go!" to send depth command

#### Heading Control
- Enter target heading in degrees (0-359)
- Click "Go!" to send heading command
- **Note**: Heading control is only available when vehicle is in ALT_HOLD mode

#### Movement Control
- Set translation throttle (0.0-1.0) - controls movement intensity
- Set duration (0.1-10 seconds) - controls how long movement lasts
- Use arrow buttons to trigger movement in desired direction:
  - ↑ Up movement
  - ↓ Down movement
  - ← Left movement
  - → Right movement

### Safety Features

- All controls are disabled until heartbeat is received
- Movement commands automatically stop after specified duration
- Comprehensive error handling and user feedback
- Real-time status monitoring

## API Endpoints

- `POST /api/connect` - Connect to vehicle
- `GET /api/status` - Get vehicle status
- `GET /api/vehicle_metrics` - Get real-time vehicle metrics via Mavlink2Rest
- `POST /api/wait_heartbeat` - Wait for vehicle heartbeat
- `POST /api/arm` - Arm/disarm vehicle
- `POST /api/set_mode` - Set vehicle mode
- `POST /api/move` - Send movement command
- `POST /api/set_depth` - Set target depth
- `POST /api/set_heading` - Set target heading
- `POST /api/set_attitude` - Set target attitude (roll, pitch, yaw)
- `POST /api/disconnect` - Disconnect from vehicle

## Technical Details

### MAVLink Commands Used

- **Heartbeat Monitoring**: Continuous monitoring of vehicle heartbeat using proper bitmask `0b10000000`
- **Arm/Disarm**: `arducopter_arm()` method for proper vehicle arming
- **Mode Setting**: `set_mode('ALT_HOLD')` for mode changes
- **Manual Control**: `MANUAL_CONTROL` messages for movement
- **Depth Control**: `set_position_target_global_int_send` with proper type mask constants (exactly matches [ArduSub documentation](https://www.ardusub.com/developers/pymavlink.html#set-target-depthattitude))
- **Heading Control**: `set_attitude_target_send` with quaternion-based attitude control (ALT_HOLD mode only)
- **Attitude Control**: Full 3-axis attitude control (roll, pitch, yaw) using `set_attitude_target_send`

### Connection Details

- **Protocol**: MAVLink over UDP
- **Port**: 14550 (standard ArduSub MAVLink port)
- **Address**: 0.0.0.0 (listens on all interfaces)

### Mavlink2Rest Integration

The extension integrates with BlueOS's Mavlink2Rest service to provide real-time vehicle metrics:

- **Current Depth**: Real-time depth reading from vehicle sensors
- **Current Heading**: Live heading/compass data
- **Arm State**: Current armed/disarmed status
- **Flight Mode**: Active vehicle mode (ALT_HOLD, MANUAL, etc.)
- **Auto-update**: Metrics refresh every 500ms for real-time display

This provides a comprehensive view of the vehicle's current state without requiring direct MAVLink connection management.

### Safety Considerations

- Always ensure vehicle is in safe location before arming
- Test controls with low throttle values first
- Monitor vehicle status continuously during operation
- Use appropriate depth and heading values for your environment

## Troubleshooting

### Common Issues

1. **No Heartbeat Received**
   - Ensure vehicle is powered on
   - Check MAVLink connection settings
   - Verify vehicle firmware is ArduSub

2. **Connection Failed**
   - Check if vehicle is accessible on network
   - Verify UDP port 14550 is open
   - Check BlueOS network configuration

3. **Commands Not Executing**
   - Ensure vehicle is armed
   - Check if vehicle is in correct mode
   - Verify heartbeat is active

### Logs

Check the BlueOS logs for detailed error information:
- Extension logs are available in the BlueOS interface
- MAVLink communication logs are displayed in the message log

## Development

### Local Development

1. Install dependencies:
```bash
cd app
pip install -r requirements.txt
```

2. Run the Flask server:
```bash
python main.py
```

3. Access the interface at `http://localhost:8000`

### Building and Testing

1. Build the Docker image:
```bash
docker build -t ardusub-pymavlink-control .
```

2. Test locally:
```bash
docker run -p 8000:8000 ardusub-pymavlink-control
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Check the BlueOS documentation
- Review ArduSub documentation
- Check the message log for error details
- Review MAVLink documentation for protocol details

## Acknowledgments

- BlueOS team for the extension framework
- ArduSub community for vehicle control protocols
- PyMavlink developers for Python MAVLink implementation
