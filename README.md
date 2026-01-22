# Ham Radio Award Coordinator

A Streamlit-based web application for coordinating multiple operators activating the same callsign in a ham radio award. This tool helps teams avoid conflicts by allowing operators to block and unblock band/mode combinations.

## Features

- **Secure Authentication**: Password-protected operator accounts with bcrypt encryption
- **Admin Access Control**: Dedicated admin panel for user management and approval
- **Operator Registration**: New operators must be approved by an admin before accessing the system
- **Band/Mode Blocking**: Reserve a band and mode combination while you're active
- **Real-time Status**: View all currently blocked bands and modes across all operators
- **Easy Unblocking**: Release your blocks when finished
- **User Management**: Admins can approve/reject registrations, revoke access, and reset passwords
- **Statistics Dashboard**: Visual representation of band usage and active operators
- **Password Management**: Users can change their own passwords; admins can reset any password
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

3. Create the first admin account (run this in the container):
```bash
docker-compose exec app python create_admin.py
```

4. Access the application at `http://localhost:8501`

5. To stop the application:
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

3. Create the first admin account:
```bash
python create_admin.py
```

4. Run the application:
```bash
streamlit run app.py
```

5. Access the application at `http://localhost:8501`

## Usage Guide

### First Time Setup (Admin)

1. Before starting, create an admin account using the setup script:
   ```bash
   python create_admin.py
   ```
2. Follow the prompts to enter your callsign, name, and password
3. Start the application and login with your admin credentials

### Operator Registration

1. New operators click "Register New Account" on the login page
2. Enter callsign, name, and password (minimum 6 characters)
3. Submit registration - the account will be pending admin approval
4. Wait for an admin to approve your registration
5. Once approved, login with your credentials

### Admin Functions

Admins have access to an additional "Admin Panel" tab with the following features:

#### Approve/Reject Pending Registrations
1. Navigate to "Admin Panel" > "Pending Approvals"
2. Review new operator registrations
3. Click "✓ Approve" to grant access or "✗ Reject" to deny

#### Manage Operators
1. Navigate to "Admin Panel" > "Manage Operators"
2. View all operators in the system with their status
3. Revoke access for approved operators if needed

#### Reset Passwords
1. Navigate to "Admin Panel" > "Reset Password"
2. Select the operator whose password needs to be reset
3. Enter and confirm the new password
4. The operator can login with the new password immediately

#### View System Statistics
1. Navigate to "Admin Panel" > "System Stats"
2. View total operators, approvals, and active blocks

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

### Changing Your Password

1. Navigate to the "Settings" tab
2. Enter your current password
3. Enter and confirm your new password (minimum 6 characters)
4. Click "Change Password"

## Data Persistence

The SQLite database is stored in the `data/` directory. When using Docker, this directory is mounted as a volume to ensure data persists across container restarts.

## Database Schema

### Operators Table
- `callsign` (TEXT, PRIMARY KEY): Operator's callsign
- `operator_name` (TEXT): Operator's name
- `password_hash` (TEXT): Bcrypt-hashed password
- `is_admin` (INTEGER): Admin flag (0 or 1)
- `is_approved` (INTEGER): Approval status (0 or 1)
- `approved_by` (TEXT): Callsign of admin who approved this operator
- `approved_at` (TIMESTAMP): When the operator was approved
- `created_at` (TIMESTAMP): Registration timestamp

### Band/Mode Blocks Table
- `id` (INTEGER, PRIMARY KEY): Unique block ID
- `operator_callsign` (TEXT): Callsign of operator who created the block
- `band` (TEXT): Ham radio band (e.g., "20m")
- `mode` (TEXT): Operating mode (e.g., "SSB")
- `blocked_at` (TIMESTAMP): When the block was created
- `UNIQUE(band, mode)`: Ensures only one operator can block each band/mode combination

## Security Features

- **Password Hashing**: All passwords are hashed using bcrypt with automatic salt generation
- **Admin Approval**: New operator registrations require admin approval before access is granted
- **Access Control**: Non-approved operators cannot login or access the system
- **Password Requirements**: Minimum 6 characters for all passwords
- **Session Management**: Secure session handling via Streamlit's built-in session state

## Port Configuration

The application runs on port 8501 by default. To change the port, modify the docker-compose.yml file or use a different port mapping:

```bash
docker run -p 8080:8501 -v $(pwd)/data:/app/data ham-coordinator
```

## License

See LICENSE file for details.
