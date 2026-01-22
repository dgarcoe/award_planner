#!/usr/bin/env python3
"""Test script for authentication and admin features."""
import os
import time
import gc

# Use a test database - MUST be set before importing database module
os.environ['DATABASE_PATH'] = 'test_auth.db'

import database as db

def wait_for_db():
    """Small delay to ensure DB operations complete."""
    time.sleep(0.1)
    gc.collect()

def run_tests():
    print("Starting authentication tests...\n")

    # Initialize database
    print("1. Initializing database...")
    db.init_database()
    print("✓ Database initialized\n")

    # Test admin creation
    print("2. Testing admin creation...")
    success, message = db.create_admin("W1ADMIN", "Admin User", "admin123")
    assert success, f"Failed to create admin: {message}"
    print(f"✓ Admin created: {message}\n")

    # Test duplicate admin creation (should warn but succeed)
    print("3. Testing duplicate admin creation...")
    success, message = db.create_admin("W1ADMIN2", "Second Admin", "admin456")
    assert success, f"Failed to create second admin: {message}"
    print(f"✓ Second admin created: {message}\n")

    # Test operator registration
    print("4. Testing operator registration...")
    success, message = db.register_operator("W1ABC", "John Doe", "password123")
    assert success, f"Failed to register operator: {message}"
    print(f"✓ Operator registered: {message}\n")

    # Test duplicate registration
    print("5. Testing duplicate registration...")
    success, message = db.register_operator("W1ABC", "John Doe 2", "password456")
    assert not success, "Should not allow duplicate registration"
    print(f"✓ Duplicate prevented: {message}\n")

    # Test authentication with unapproved account
    print("6. Testing login with unapproved account...")
    success, message, operator = db.authenticate_operator("W1ABC", "password123")
    assert not success, "Should not allow unapproved operator to login"
    assert "pending" in message.lower(), f"Expected pending message, got: {message}"
    print(f"✓ Unapproved login blocked: {message}\n")

    # Test wrong password
    print("7. Testing login with wrong password...")
    success, message, operator = db.authenticate_operator("W1ADMIN", "wrongpassword")
    assert not success, "Should not allow login with wrong password"
    print(f"✓ Wrong password rejected: {message}\n")

    # Test admin login
    print("8. Testing admin login...")
    success, message, operator = db.authenticate_operator("W1ADMIN", "admin123")
    assert success, f"Admin login failed: {message}"
    assert operator['is_admin'] == 1, "Admin flag not set"
    assert operator['is_approved'] == 1, "Admin should be auto-approved"
    print(f"✓ Admin login successful: {message}\n")

    # Test getting pending operators
    print("9. Testing pending operators list...")
    wait_for_db()
    pending = db.get_pending_operators()
    assert len(pending) == 1, f"Expected 1 pending operator, got {len(pending)}"
    assert pending[0]['callsign'] == "W1ABC", "Wrong pending operator"
    print(f"✓ Found {len(pending)} pending operator(s)\n")

    # Test approving operator
    print("10. Testing operator approval...")
    wait_for_db()
    success, message = db.approve_operator("W1ABC", "W1ADMIN")
    assert success, f"Failed to approve operator: {message}"
    print(f"✓ Operator approved: {message}\n")

    # Test approved operator login
    print("11. Testing login with approved account...")
    success, message, operator = db.authenticate_operator("W1ABC", "password123")
    assert success, f"Approved login failed: {message}"
    assert operator['is_approved'] == 1, "Operator should be approved"
    assert operator['is_admin'] == 0, "Regular operator should not be admin"
    print(f"✓ Approved operator login successful\n")

    # Test password change
    print("12. Testing password change...")
    success, message = db.change_password("W1ABC", "password123", "newpassword456")
    assert success, f"Failed to change password: {message}"
    print(f"✓ Password changed: {message}\n")

    # Test login with new password
    print("13. Testing login with new password...")
    success, message, operator = db.authenticate_operator("W1ABC", "newpassword456")
    assert success, f"Login with new password failed: {message}"
    print(f"✓ Login with new password successful\n")

    # Test old password doesn't work
    print("14. Testing that old password is rejected...")
    success, message, operator = db.authenticate_operator("W1ABC", "password123")
    assert not success, "Old password should not work"
    print(f"✓ Old password correctly rejected\n")

    # Test admin password reset
    print("15. Testing admin password reset...")
    success, message = db.admin_reset_password("W1ABC", "resetpassword789", "W1ADMIN")
    assert success, f"Failed to reset password: {message}"
    print(f"✓ Admin reset password: {message}\n")

    # Test login with reset password
    print("16. Testing login with reset password...")
    success, message, operator = db.authenticate_operator("W1ABC", "resetpassword789")
    assert success, f"Login with reset password failed: {message}"
    print(f"✓ Login with reset password successful\n")

    # Test revoking access
    print("17. Testing access revocation...")
    # First create a block
    db.block_band_mode("W1ABC", "20m", "SSB")
    success, message = db.revoke_operator_access("W1ABC")
    assert success, f"Failed to revoke access: {message}"
    print(f"✓ Access revoked: {message}\n")

    # Test revoked operator cannot login
    print("18. Testing login after revocation...")
    success, message, operator = db.authenticate_operator("W1ABC", "resetpassword789")
    assert not success, "Revoked operator should not be able to login"
    print(f"✓ Revoked operator login blocked: {message}\n")

    # Test all operators list
    print("19. Testing all operators list...")
    operators = db.get_all_operators()
    assert len(operators) >= 2, f"Expected at least 2 operators, got {len(operators)}"
    print(f"✓ Retrieved {len(operators)} operator(s)\n")

    # Test registering new operator and rejecting
    print("20. Testing operator rejection...")
    success, message = db.register_operator("W1XYZ", "Jane Smith", "password999")
    assert success, f"Failed to register operator: {message}"
    success, message = db.reject_operator("W1XYZ")
    assert success, f"Failed to reject operator: {message}"
    print(f"✓ Operator rejected: {message}\n")

    print("=" * 50)
    print("All authentication tests passed successfully!")
    print("=" * 50)

    # Cleanup
    try:
        os.remove('test_auth.db')
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
