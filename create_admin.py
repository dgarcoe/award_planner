#!/usr/bin/env python3
"""
Admin Account Creation Script

This script creates an administrator account for the Ham Radio Award Coordinator.
Run this script before starting the application for the first time to create the initial admin user.

Usage:
    python create_admin.py
"""

import database as db
import getpass
import sys

def create_admin_account():
    """Interactive admin account creation."""
    print("=" * 60)
    print("Ham Radio Award Coordinator - Admin Account Setup")
    print("=" * 60)
    print()

    # Initialize database
    print("Initializing database...")
    db.init_database()
    print("✓ Database initialized")
    print()

    # Get admin details
    print("Enter admin details:")
    print("-" * 60)

    callsign = input("Admin Callsign: ").strip().upper()
    if not callsign:
        print("❌ Error: Callsign cannot be empty")
        sys.exit(1)

    operator_name = input("Admin Name: ").strip()
    if not operator_name:
        print("❌ Error: Name cannot be empty")
        sys.exit(1)

    # Get password with confirmation
    while True:
        password = getpass.getpass("Admin Password (min 6 characters): ")
        if len(password) < 6:
            print("❌ Password must be at least 6 characters. Please try again.")
            continue

        password_confirm = getpass.getpass("Confirm Password: ")
        if password != password_confirm:
            print("❌ Passwords do not match. Please try again.")
            continue

        break

    print()
    print("Creating admin account...")

    # Create admin account
    success, message = db.create_admin(callsign, operator_name, password)

    if success:
        print(f"✓ {message}")
        print()
        print("=" * 60)
        print("Admin account created successfully!")
        print("=" * 60)
        print()
        print(f"Callsign: {callsign}")
        print(f"Name: {operator_name}")
        print()
        print("You can now start the application and login with these credentials.")
        print("Command: streamlit run app.py")
        print()
    else:
        print(f"❌ Error: {message}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        create_admin_account()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
