# Ham Radio Award Coordinator

A Streamlit-based web application for coordinating multiple operators activating the same callsign in a ham radio award. This tool helps teams avoid conflicts by allowing operators to block and unblock band/mode combinations.

## Features

- **Operator Registration**: Simple login/registration system using callsign and operator name
- **Band/Mode Blocking**: Reserve a band and mode combination while you're active
- **Real-time Status**: View all currently blocked bands and modes across all operators
- **Easy Unblocking**: Release your blocks when finished
- **Statistics Dashboard**: Visual representation of band usage and active operators
- **SQLite Database**: Persistent storage of all coordination data
- **Dockerized**: Easy deployment using Docker

## Supported Bands

160m, 80m, 60m, 40m, 30m, 20m, 17m, 15m, 12m, 10m, 6m, 2m, 70cm

## Supported Modes

SSB, CW, FM, RTTY, FT8, FT4, PSK31, SSTV, AM

## Installation & Usage

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd award_planner
```

2. Build and run with docker-compose:
```bash
docker-compose up -d
```

3. Access the application at `http://localhost:8501`

4. To stop the application:
```bash
docker-compose down
```

### Using Docker manually

```bash
docker build -t ham-coordinator .
docker run -p 8501:8501 -v $(pwd)/data:/app/data ham-coordinator
```

### Local Installation

1. Install Python 3.11 or higher

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run app.py
```

4. Access the application at `http://localhost:8501`

## Usage Guide

### First Time Setup

1. Open the application in your web browser
2. Enter your callsign (will be converted to uppercase)
3. Enter your operator name
4. Click "Login / Register"

### Blocking a Band/Mode

1. Navigate to the "Block Band/Mode" tab
2. Select the band you want to use
3. Select the mode you want to use
4. Click "Block"
5. The system will confirm if the block was successful or if it's already in use

### Unblocking a Band/Mode

1. Navigate to the "Unblock Band/Mode" tab
2. You'll see a list of your active blocks
3. Click "Unblock" next to the band/mode you want to release

### Viewing Current Status

1. Navigate to the "Current Status" tab
2. View all active blocks across all operators
3. See summary statistics including:
   - Total number of blocks
   - Number of active operators
   - Number of bands in use
   - Visual chart of band usage

## Data Persistence

The SQLite database is stored in the `data/` directory. When using Docker, this directory is mounted as a volume to ensure data persists across container restarts.

## Database Schema

### Operators Table
- `callsign` (TEXT, PRIMARY KEY): Operator's callsign
- `operator_name` (TEXT): Operator's name
- `created_at` (TIMESTAMP): Registration timestamp

### Band/Mode Blocks Table
- `id` (INTEGER, PRIMARY KEY): Unique block ID
- `operator_callsign` (TEXT): Callsign of operator who created the block
- `band` (TEXT): Ham radio band (e.g., "20m")
- `mode` (TEXT): Operating mode (e.g., "SSB")
- `blocked_at` (TIMESTAMP): When the block was created
- `UNIQUE(band, mode)`: Ensures only one operator can block each band/mode combination

## Port Configuration

The application runs on port 8501 by default. To change the port, modify the docker-compose.yml file or use a different port mapping:

```bash
docker run -p 8080:8501 -v $(pwd)/data:/app/data ham-coordinator
```

## License

See LICENSE file for details.
