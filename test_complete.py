#!/usr/bin/env python3
"""Complete test script including admin roles and translations."""
import os
import gc

# Use a test database - MUST be set before importing database module
os.environ['DATABASE_PATH'] = 'test_complete.db'

import database as db
from translations import get_text, AVAILABLE_LANGUAGES

def wait_for_db():
    """Small delay to ensure DB operations complete."""
    gc.collect()

def run_tests():
    print("Starting complete system tests...\n")

    # Initialize database
    print("1. Initializing database...")
    db.init_database()
    print("✓ Database initialized\n")

    # Test operator creation
    print("2. Testing operator creation (regular)...")
    success, message = db.create_operator("W1ABC", "John Doe", "password123", is_admin=False)
    assert success, f"Failed to create operator: {message}"
    print(f"✓ Operator created: {message}\n")

    # Test operator creation with admin flag
    print("3. Testing operator creation (admin)...")
    success, message = db.create_operator("W1XYZ", "Jane Smith", "password456", is_admin=True)
    assert success, f"Failed to create admin operator: {message}"
    assert "(admin)" in message.lower(), "Admin flag not mentioned in message"
    print(f"✓ Admin operator created: {message}\n")

    # Test authentication and verify admin flag
    print("4. Testing admin operator authentication...")
    wait_for_db()
    success, message, operator = db.authenticate_operator("W1XYZ", "password456")
    assert success, f"Authentication failed: {message}"
    assert operator['is_admin'] == 1, "Admin flag not set correctly"
    print(f"✓ Admin authenticated with is_admin={operator['is_admin']}\n")

    # Test regular operator authentication
    print("5. Testing regular operator authentication...")
    success, message, operator = db.authenticate_operator("W1ABC", "password123")
    assert success, f"Authentication failed: {message}"
    assert operator['is_admin'] == 0, "Regular operator should not have admin flag"
    print(f"✓ Regular operator authenticated with is_admin={operator['is_admin']}\n")

    # Test get_all_operators includes is_admin
    print("6. Testing get_all_operators...")
    wait_for_db()
    operators = db.get_all_operators()
    assert len(operators) == 2, f"Expected 2 operators, got {len(operators)}"
    assert 'is_admin' in operators[0], "is_admin field missing"
    admin_count = sum(1 for op in operators if op['is_admin'])
    assert admin_count == 1, f"Expected 1 admin, got {admin_count}"
    print(f"✓ Retrieved {len(operators)} operators, {admin_count} admin(s)\n")

    # Test promote to admin
    print("7. Testing promote to admin...")
    wait_for_db()
    success, message = db.promote_to_admin("W1ABC")
    assert success, f"Failed to promote: {message}"
    assert "promoted" in message.lower(), "Unexpected success message"
    print(f"✓ {message}\n")

    # Verify promotion
    print("8. Verifying promotion...")
    wait_for_db()
    operator = db.get_operator("W1ABC")
    assert operator is not None, "Operator not found after promotion"
    assert operator['is_admin'] == 1, "Operator not promoted correctly"
    print(f"✓ Promotion verified: is_admin={operator['is_admin']}\n")

    # Test promote already-admin operator
    print("9. Testing promote already-admin operator...")
    success, message = db.promote_to_admin("W1ABC")
    assert not success, "Should not allow promoting an admin"
    assert "already" in message.lower(), "Unexpected error message"
    print(f"✓ Correctly prevented: {message}\n")

    # Test demote from admin
    print("10. Testing demote from admin...")
    wait_for_db()
    success, message = db.demote_from_admin("W1ABC")
    assert success, f"Failed to demote: {message}"
    assert "demoted" in message.lower(), "Unexpected success message"
    print(f"✓ {message}\n")

    # Verify demotion
    print("11. Verifying demotion...")
    wait_for_db()
    operator = db.get_operator("W1ABC")
    assert operator is not None, "Operator not found after demotion"
    assert operator['is_admin'] == 0, "Operator not demoted correctly"
    print(f"✓ Demotion verified: is_admin={operator['is_admin']}\n")

    # Test demote non-admin operator
    print("12. Testing demote non-admin operator...")
    success, message = db.demote_from_admin("W1ABC")
    assert not success, "Should not allow demoting a non-admin"
    assert "not an admin" in message.lower(), "Unexpected error message"
    print(f"✓ Correctly prevented: {message}\n")

    # Test translations
    print("13. Testing translations...")
    en_text = get_text('app_title', 'en')
    es_text = get_text('app_title', 'es')
    assert en_text == "Ham Radio Award Coordinator", f"Expected English title, got: {en_text}"
    assert es_text == "Coordinador de Premios de Radio Aficionados", f"Expected Spanish title, got: {es_text}"
    print(f"✓ Translations working: EN='{en_text[:20]}...', ES='{es_text[:20]}...'\n")

    # Test available languages
    print("14. Testing available languages...")
    assert 'en' in AVAILABLE_LANGUAGES, "English not in available languages"
    assert 'es' in AVAILABLE_LANGUAGES, "Spanish not in available languages"
    assert AVAILABLE_LANGUAGES['en'] == 'English', "English language name incorrect"
    assert AVAILABLE_LANGUAGES['es'] == 'Español', "Spanish language name incorrect"
    print(f"✓ Available languages: {', '.join(f'{k}={v}' for k, v in AVAILABLE_LANGUAGES.items())}\n")

    # Test blocking/unblocking still works
    print("15. Testing band/mode blocking...")
    wait_for_db()
    success, message = db.block_band_mode("W1XYZ", "20m", "SSB")
    assert success, f"Failed to block: {message}"
    print(f"✓ Blocked: {message}\n")

    print("16. Testing unblocking...")
    wait_for_db()
    success, message = db.unblock_band_mode("W1XYZ", "20m", "SSB")
    assert success, f"Failed to unblock: {message}"
    print(f"✓ Unblocked: {message}\n")

    print("=" * 50)
    print("All complete system tests passed successfully!")
    print("=" * 50)

    # Cleanup
    try:
        os.remove('test_complete.db')
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
