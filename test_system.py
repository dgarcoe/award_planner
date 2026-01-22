#!/usr/bin/env python3
"""Test script for the simplified authentication system."""
import os
import gc

# Use a test database - MUST be set before importing database module
os.environ['DATABASE_PATH'] = 'test_system.db'

import database as db

def wait_for_db():
    """Small delay to ensure DB operations complete."""
    gc.collect()

def run_tests():
    print("Starting system tests...\n")

    # Initialize database
    print("1. Initializing database...")
    db.init_database()
    print("✓ Database initialized\n")

    # Test operator creation
    print("2. Testing operator creation...")
    success, message = db.create_operator("W1ABC", "John Doe", "password123")
    assert success, f"Failed to create operator: {message}"
    print(f"✓ Operator created: {message}\n")

    # Test duplicate creation
    print("3. Testing duplicate operator prevention...")
    success, message = db.create_operator("W1ABC", "Jane Doe", "password456")
    assert not success, "Should not allow duplicate callsign"
    assert "already exists" in message.lower(), f"Expected 'already exists' in message, got: {message}"
    print(f"✓ Duplicate prevented: {message}\n")

    # Test operator authentication
    print("4. Testing operator authentication...")
    wait_for_db()
    success, message, operator = db.authenticate_operator("W1ABC", "password123")
    assert success, f"Authentication failed: {message}"
    assert operator is not None, "Operator data not returned"
    assert operator['callsign'] == "W1ABC", "Wrong callsign"
    print(f"✓ Authentication successful\n")

    # Test wrong password
    print("5. Testing wrong password...")
    success, message, operator = db.authenticate_operator("W1ABC", "wrongpassword")
    assert not success, "Should not authenticate with wrong password"
    assert operator is None, "Should not return operator data"
    print(f"✓ Wrong password rejected: {message}\n")

    # Test password change
    print("6. Testing password change...")
    wait_for_db()
    success, message = db.change_password("W1ABC", "password123", "newpassword456")
    assert success, f"Failed to change password: {message}"
    print(f"✓ Password changed: {message}\n")

    # Test login with new password
    print("7. Testing login with new password...")
    wait_for_db()
    success, message, operator = db.authenticate_operator("W1ABC", "newpassword456")
    assert success, f"Login with new password failed: {message}"
    print(f"✓ Login with new password successful\n")

    # Test old password doesn't work
    print("8. Testing old password rejection...")
    success, message, operator = db.authenticate_operator("W1ABC", "password123")
    assert not success, "Old password should not work"
    print(f"✓ Old password rejected\n")

    # Test admin password reset
    print("9. Testing admin password reset...")
    wait_for_db()
    success, message = db.admin_reset_password("W1ABC", "adminreset789")
    assert success, f"Failed to reset password: {message}"
    print(f"✓ Password reset: {message}\n")

    # Test login with reset password
    print("10. Testing login with reset password...")
    wait_for_db()
    success, message, operator = db.authenticate_operator("W1ABC", "adminreset789")
    assert success, f"Login with reset password failed: {message}"
    print(f"✓ Login with reset password successful\n")

    # Test blocking band/mode
    print("11. Testing band/mode blocking...")
    wait_for_db()
    success, message = db.block_band_mode("W1ABC", "20m", "SSB")
    assert success, f"Failed to block: {message}"
    print(f"✓ Band/mode blocked: {message}\n")

    # Test duplicate block prevention
    print("12. Testing duplicate block prevention...")
    db.create_operator("W1XYZ", "Jane Smith", "password999")
    success, message = db.block_band_mode("W1XYZ", "20m", "SSB")
    assert not success, "Should not allow duplicate block"
    print(f"✓ Duplicate block prevented: {message}\n")

    # Test unblocking
    print("13. Testing unblock...")
    wait_for_db()
    success, message = db.unblock_band_mode("W1ABC", "20m", "SSB")
    assert success, f"Failed to unblock: {message}"
    print(f"✓ Unblocked: {message}\n")

    # Test getting all operators
    print("14. Testing get all operators...")
    wait_for_db()
    operators = db.get_all_operators()
    assert len(operators) == 2, f"Expected 2 operators, got {len(operators)}"
    print(f"✓ Retrieved {len(operators)} operators\n")

    # Test operator deletion
    print("15. Testing operator deletion...")
    wait_for_db()
    # Create a block first
    db.block_band_mode("W1XYZ", "40m", "CW")
    success, message = db.delete_operator("W1XYZ")
    assert success, f"Failed to delete operator: {message}"
    print(f"✓ Operator deleted: {message}\n")

    # Verify deletion
    print("16. Verifying operator deletion...")
    wait_for_db()
    operators = db.get_all_operators()
    assert len(operators) == 1, f"Expected 1 operator after deletion, got {len(operators)}"
    print(f"✓ Deletion verified\n")

    print("=" * 50)
    print("All system tests passed successfully!")
    print("=" * 50)

    # Cleanup
    try:
        os.remove('test_system.db')
        print("\nTest database cleaned up.")
    except FileNotFoundError:
        print("\nTest database already cleaned up.")

if __name__ == "__main__":
    try:
        run_tests()
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
