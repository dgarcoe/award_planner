# QuendAward: Ham Radio Award Operator Coordination Tool

A Streamlit-based web application for coordinating multiple operators activating the same callsign in ham radio awards. This tool helps teams avoid conflicts by allowing operators to block and unblock band/mode combinations, manage multiple awards, and visualize real-time activity.

## Features

- **Award Management**: Create and manage multiple awards with start/end dates and descriptions
- **Award Selection**: Operators can select which award they want to work on
- **Activity Dashboard**: Real-time heatmap showing band/mode availability with interactive visualizations
- **Environment-Based Admin Access**: Super admin credentials configured via environment variables
- **Admin Role Management**: Promote/demote operators to/from admin role
- **Flexible Admin System**: Support for multiple admins (env-based super admin + database admins)
- **Admin User Management**: Admins create operator accounts and provide credentials
- **Multi-Language Support**: Full interface translation in English, Spanish, and Galician (default)
- **Language Selector**: Switch between languages on-the-fly
- **One Block Per Operator**: Operators can only have one active block at a time (auto-releases previous)
- **Auto-Release on Logout**: All blocks automatically released when operator logs out
- **Admin Block Management**: Admins can release any operator's blocks
- **Timeline Visualization**: Interactive heatmap showing all band/mode combinations and their status
- **Statistics Dashboard**: Visual charts and metrics for band usage and operator activity
- **Secure Authentication**: Password-protected accounts with bcrypt encryption
- **Band/Mode Blocking**: Reserve a band and mode combination while you're active
- **Real-time Status**: View all currently blocked bands and modes across all operators
- **Easy Unblocking**: Release your blocks when finished
- **Password Management**: Users can change their passwords; admins can reset any password
- **SQLite Database**: Persistent storage of all coordination data
- **Dockerized**: Easy deployment using Docker
- **Clean Code Architecture**: Modular design with separated concerns for easy maintenance

## Supported Bands

160m, 80m, 60m, 40m, 30m, 20m, 17m, 15m, 12m, 10m, 6m, 2m, 70cm

## Supported Modes

CW, SSB, FT4, FT8, RTTY, PSK

## Code Architecture

The application follows clean code principles with a modular architecture:

```
award_planner/
├── app.py                 # Main application entry point (289 lines)
├── config.py              # Configuration constants (22 lines)
├── charts.py              # Chart creation functions (117 lines)
├── ui_components.py       # Reusable UI components (172 lines)
├── admin_functions.py     # Admin panel functions (287 lines)
├── database.py            # Database operations
├── translations.py        # Multi-language translations
└── data/                  # SQLite database storage
```

### Module Responsibilities

- **config.py**: Constants (bands, modes, colors, credentials)
- **charts.py**: Plotly chart generation (heatmap, bar charts)
- **ui_components.py**: Reusable UI components (selectors, dashboards)
- **admin_functions.py**: Admin panel tab implementations
- **app.py**: Application orchestration and page routing

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

5. Login with your admin credentials (interface will be in Galician by default)

6. To stop the application:
```bash
docker-compose down
```

### Using Docker manually

```bash
docker build -t quendaward .
docker run -p 8501:8501 \
  -e ADMIN_CALLSIGN=W1ADMIN \
  -e ADMIN_PASSWORD=SecurePassword123 \
  -v $(pwd)/data:/app/data \
  quendaward
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
3. Login with your admin credentials (default language is Galician)

### Creating Awards (Admin Only)

1. Login as admin
2. Navigate to "Admin Panel" > "Manage Awards"
3. Enter award name, description, start date, and end date
4. Click "Create Award"
5. Toggle award status (Active/Inactive) as needed
6. Only active awards are visible to operators

### Creating Operators (Admin Only)

1. Login as admin
2. Navigate to "Admin Panel" > "Create Operator"
3. Enter the operator's callsign, name, and password
4. (Optional) Check "Grant admin privileges" to create the operator as an admin
5. Click "Create Operator"
6. The system will display the credentials to provide to the operator
7. Give these credentials to the operator securely

### Operator Login

1. Operators use the credentials provided by the admin
2. Enter callsign and password on the login page
3. Click "Login"
4. Select the award you want to work on

### Language Selection

1. Use the language selector in the top-right corner (login page) or top-middle (operator panel)
2. Choose between English, Español, or Galego
3. The interface will immediately switch to the selected language
4. Language preference is maintained during your session
5. Default language is Galician (Galego)

### Admin Functions

#### Create Operators
1. Navigate to "Admin Panel" > "Create Operator"
2. Fill in callsign, name, and password
3. Check "Grant admin privileges" to create as admin (optional)
4. System displays credentials to give to the operator

#### Manage Operators
1. Navigate to "Admin Panel" > "Manage Operators"
2. View all operators in the system with admin status
3. Delete operators if needed (removes their blocks too)

#### Manage Admin Roles
1. Navigate to "Admin Panel" > "Manage Admins"
2. **Promote to Admin**: Select a regular operator and click "Promote to Admin"
3. **Demote from Admin**: Select an admin operator and click "Demote from Admin"
4. Note: Env-based super admin cannot be demoted

#### Reset Passwords
1. Navigate to "Admin Panel" > "Reset Password"
2. Select the operator
3. Enter and confirm new password
4. System displays the new password to give to the operator

#### Manage All Blocks (Admin)
1. Navigate to "Admin Panel" > "Manage Blocks"
2. Filter blocks by award
3. View all active blocks with operator information
4. Click "Unblock" next to any block to release it
5. Useful for resolving stuck blocks or helping operators who forgot to unblock

#### Manage Awards (Admin)
1. Navigate to "Admin Panel" > "Manage Awards"
2. Create new awards with name, description, and date range
3. Toggle award status (Active/Inactive)
4. Delete awards if needed
5. Only active awards are visible to operators

#### View System Statistics
1. Navigate to "Admin Panel" > "System Stats"
2. View total operators, active operators, active blocks, and total admins

### Blocking a Band/Mode

**Important**: Each operator can only have one active block at a time. If you block a new band/mode while already having a block, your previous block will automatically be released.

1. Navigate to the "Block Band/Mode" tab
2. Select the award you want to work on
3. Select the band you want to use
4. Select the mode you want to use
5. Click "Block"
6. The system will confirm if the block was successful or if it's already in use

### Unblocking a Band/Mode

1. Navigate to the "Block Band/Mode" tab
2. You'll see a list of your active blocks below the blocking section
3. Click "Unblock" next to the band/mode you want to release

### Activity Dashboard

1. Navigate to the "Activity Dashboard" tab (📊)
2. View the interactive heatmap showing:
   - **Green cells**: Available band/mode combinations (shows "Libre"/"Free")
   - **Red cells**: Blocked band/mode combinations (shows operator callsign)
3. Hover over cells to see detailed information:
   - Band and mode
   - Operator name and callsign (if blocked)
   - Time when block was created
4. View summary statistics:
   - Total number of blocks
   - Number of active operators
   - Number of bands in use
5. View the "Blocks by Band" chart showing distribution across bands
6. Dashboard auto-refreshes every 5 seconds for real-time updates

### Logging Out

When you click the "Logout" button, the system automatically releases all your active blocks. This ensures that frequency allocations don't remain locked when you're no longer active.

### Changing Your Password (Operators Only)

1. Navigate to the "Settings" tab
2. Enter your current password
3. Enter and confirm your new password (minimum 6 characters)
4. Click "Change Password"

Note: Env-based admin password is set via environment variables and cannot be changed in the UI.

## Data Persistence

The SQLite database is stored in the `data/` directory. When using Docker, this directory is mounted as a volume to ensure data persists across container restarts.

## Database Schema

### Operators Table
- `callsign` (TEXT, PRIMARY KEY): Operator's callsign
- `operator_name` (TEXT): Operator's name
- `password_hash` (TEXT): Bcrypt-hashed password
- `is_admin` (INTEGER): Admin flag (0 = regular operator, 1 = admin)
- `created_at` (TIMESTAMP): Account creation timestamp

### Band/Mode Blocks Table
- `id` (INTEGER, PRIMARY KEY): Unique block ID
- `operator_callsign` (TEXT): Callsign of operator who created the block
- `band` (TEXT): Ham radio band (e.g., "20m")
- `mode` (TEXT): Operating mode (e.g., "SSB")
- `blocked_at` (TIMESTAMP): When the block was created
- `award_id` (INTEGER): Foreign key to awards table
- `UNIQUE(band, mode, award_id)`: Ensures only one operator can block each band/mode combination per award

### Awards Table
- `id` (INTEGER, PRIMARY KEY): Unique award ID
- `name` (TEXT): Award name
- `description` (TEXT): Award description
- `start_date` (TEXT): Award start date
- `end_date` (TEXT): Award end date
- `is_active` (INTEGER): Active flag (0 = inactive, 1 = active)
- `created_at` (TIMESTAMP): Award creation timestamp

## Security Features

- **Dual-Level Admin System**:
  - Super admin via environment variables (cannot be modified or deleted)
  - Database admins that can be promoted/demoted
- **Password Hashing**: All operator passwords hashed using bcrypt with automatic salt generation
- **Admin-Only User Creation**: Only admins can create operator accounts
- **Admin Role Management**: Promote regular operators to admin or demote admins
- **Password Requirements**: Minimum 6 characters for all passwords
- **Session Management**: Secure session handling via Streamlit's built-in session state
- **Award Isolation**: Blocks are isolated per award to prevent conflicts

## Internationalization

- **Multi-Language Support**: Full interface available in English, Spanish, and Galician
- **Default Language**: Galician (Galego) 🎯
- **Languages Available**: 🇬🇧 English, 🇪🇸 Español, 🇬🇱 Galego
- **Easy Language Switching**: Toggle between languages with a single click
- **Session-Based Language Preference**: Language selection maintained during your session
- **Fully Translated**: All UI elements, menus, messages, and labels are translated
- **Extensible**: Architecture supports adding more languages easily

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
  quendaward
```

## Development

### Code Organization

The codebase follows clean code principles:

- **Separation of Concerns**: Each module has a single responsibility
- **DRY Principle**: Reusable components reduce code duplication
- **Modularity**: Easy to test and maintain individual components
- **Clear Naming**: Descriptive function and variable names
- **Documentation**: Docstrings for all major functions

### Running Tests

```bash
python -m pytest
```

## License

See LICENSE file for details.
