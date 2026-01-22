# Ham Radio Award Coordinator

A Streamlit-based web application for coordinating multiple operators activating the same callsign in a ham radio award. This tool helps teams avoid conflicts by allowing operators to block and unblock band/mode combinations.

## Features

- **Environment-Based Admin Access**: Admin credentials configured via environment variables
- **Admin User Management**: Admins create operator accounts and provide credentials
- **Secure Authentication**: Password-protected accounts with bcrypt encryption
- **Band/Mode Blocking**: Reserve a band and mode combination while you're active
- **Real-time Status**: View all currently blocked bands and modes across all operators
- **Easy Unblocking**: Release your blocks when finished
- **Password Management**: Users can change their passwords; admins can reset any password
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

2. Create a `.env` file with admin credentials:
```bash
cp .env.example .env
# Edit .env and set your admin credentials
```

Example `.env` file:
```
ADMIN_CALLSIGN=W1ADMIN
ADMIN_PASSWORD=SecurePassword123
```

3. Build and run with docker-compose:
```bash
docker-compose up -d
```

4. Access the application at `http://localhost:8501`

5. Login with your admin credentials

6. To stop the application:
```bash
docker-compose down
```

### Using Docker manually

```bash
docker build -t ham-coordinator .
docker run -p 8501:8501 \
  -e ADMIN_CALLSIGN=W1ADMIN \
  -e ADMIN_PASSWORD=SecurePassword123 \
  -v $(pwd)/data:/app/data \
  ham-coordinator
```

### Local Installation

1. Install Python 3.11 or higher

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables:
```bash
export ADMIN_CALLSIGN=W1ADMIN
export ADMIN_PASSWORD=SecurePassword123
```

4. Run the application:
```bash
streamlit run app.py
```

5. Access the application at `http://localhost:8501`

## Usage Guide

### Admin Setup

1. Set admin credentials via environment variables:
   - `ADMIN_CALLSIGN`: Your admin callsign (e.g., W1ADMIN)
   - `ADMIN_PASSWORD`: Secure password for admin access

2. Start the application
3. Login with your admin credentials

### Creating Operators (Admin Only)

1. Login as admin
2. Navigate to "Admin Panel" > "Create Operator"
3. Enter the operator's callsign, name, and password
4. Click "Create Operator"
5. The system will display the credentials to provide to the operator
6. Give these credentials to the operator securely

### Operator Login

1. Operators use the credentials provided by the admin
2. Enter callsign and password on the login page
3. Click "Login"

### Admin Functions

#### Create Operators
1. Navigate to "Admin Panel" > "Create Operator"
2. Fill in callsign, name, and password
3. System displays credentials to give to the operator

#### Manage Operators
1. Navigate to "Admin Panel" > "Manage Operators"
2. View all operators in the system
3. Delete operators if needed (removes their blocks too)

#### Reset Passwords
1. Navigate to "Admin Panel" > "Reset Password"
2. Select the operator
3. Enter and confirm new password
4. System displays the new password to give to the operator

#### View System Statistics
1. Navigate to "Admin Panel" > "System Stats"
2. View total operators and active blocks

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

### Changing Your Password (Operators Only)

1. Navigate to the "Settings" tab
2. Enter your current password
3. Enter and confirm your new password (minimum 6 characters)
4. Click "Change Password"

Note: Admin password is set via environment variables and cannot be changed in the UI.

## Data Persistence

The SQLite database is stored in the `data/` directory. When using Docker, this directory is mounted as a volume to ensure data persists across container restarts.

## Database Schema

### Operators Table
- `callsign` (TEXT, PRIMARY KEY): Operator's callsign
- `operator_name` (TEXT): Operator's name
- `password_hash` (TEXT): Bcrypt-hashed password
- `created_at` (TIMESTAMP): Account creation timestamp

### Band/Mode Blocks Table
- `id` (INTEGER, PRIMARY KEY): Unique block ID
- `operator_callsign` (TEXT): Callsign of operator who created the block
- `band` (TEXT): Ham radio band (e.g., "20m")
- `mode` (TEXT): Operating mode (e.g., "SSB")
- `blocked_at` (TIMESTAMP): When the block was created
- `UNIQUE(band, mode)`: Ensures only one operator can block each band/mode combination

## Security Features

- **Environment-Based Admin**: Admin credentials stored in environment variables, not database
- **Password Hashing**: All operator passwords hashed using bcrypt with automatic salt generation
- **Admin-Only User Creation**: Only admins can create operator accounts
- **Password Requirements**: Minimum 6 characters for all passwords
- **Session Management**: Secure session handling via Streamlit's built-in session state

## Environment Variables

Required environment variables:

- `ADMIN_CALLSIGN`: Admin callsign (e.g., W1ADMIN)
- `ADMIN_PASSWORD`: Admin password

Optional environment variables:

- `DATABASE_PATH`: Path to SQLite database file (default: `ham_coordinator.db`)

## Port Configuration

The application runs on port 8501 by default. To change the port, modify the docker-compose.yml file or use a different port mapping:

```bash
docker run -p 8080:8501 \
  -e ADMIN_CALLSIGN=W1ADMIN \
  -e ADMIN_PASSWORD=SecurePassword123 \
  -v $(pwd)/data:/app/data \
  ham-coordinator
```

## License

See LICENSE file for details.
