#!/usr/bin/env python3
"""Simple test script to verify database functionality."""
import database as db
import os

# Use a test database
os.environ['DATABASE_PATH'] = 'test_ham_coordinator.db'

def run_tests():
    print("Starting database tests...\n")

    # Initialize database
    print("1. Initializing database...")
    db.init_database()
    print("✓ Database initialized\n")

    # Test operator registration
    print("2. Testing operator registration...")
    success = db.register_operator("W1ABC", "John Doe")
    assert success, "Failed to register operator"
    print("✓ Operator registered\n")

    # Test getting operator
    print("3. Testing operator retrieval...")
    operator = db.get_operator("W1ABC")
    assert operator is not None, "Failed to retrieve operator"
    assert operator['callsign'] == "W1ABC", "Callsign mismatch"
    assert operator['operator_name'] == "John Doe", "Name mismatch"
    print(f"✓ Retrieved operator: {operator['callsign']} - {operator['operator_name']}\n")

    # Test blocking a band/mode
    print("4. Testing band/mode blocking...")
    success, message = db.block_band_mode("W1ABC", "20m", "SSB")
    assert success, f"Failed to block: {message}"
    print(f"✓ Blocked 20m/SSB: {message}\n")

    # Test duplicate blocking
    print("5. Testing duplicate block prevention...")
    success, message = db.block_band_mode("W1XYZ", "20m", "SSB")
    assert not success, "Should not allow duplicate block"
    print(f"✓ Duplicate block prevented: {message}\n")

    # Test getting all blocks
    print("6. Testing retrieval of all blocks...")
    blocks = db.get_all_blocks()
    assert len(blocks) == 1, f"Expected 1 block, got {len(blocks)}"
    print(f"✓ Retrieved {len(blocks)} block(s)\n")

    # Test getting operator blocks
    print("7. Testing retrieval of operator blocks...")
    my_blocks = db.get_operator_blocks("W1ABC")
    assert len(my_blocks) == 1, f"Expected 1 block for W1ABC, got {len(my_blocks)}"
    print(f"✓ Retrieved {len(my_blocks)} block(s) for W1ABC\n")

    # Test unblocking by wrong operator
    print("8. Testing unblock by wrong operator...")
    db.register_operator("W1XYZ", "Jane Smith")
    success, message = db.unblock_band_mode("W1XYZ", "20m", "SSB")
    assert not success, "Should not allow unblock by different operator"
    print(f"✓ Prevented unauthorized unblock: {message}\n")

    # Test unblocking by correct operator
    print("9. Testing unblock by correct operator...")
    success, message = db.unblock_band_mode("W1ABC", "20m", "SSB")
    assert success, f"Failed to unblock: {message}"
    print(f"✓ Unblocked 20m/SSB: {message}\n")

    # Verify block was removed
    print("10. Verifying block removal...")
    blocks = db.get_all_blocks()
    assert len(blocks) == 0, f"Expected 0 blocks, got {len(blocks)}"
    print(f"✓ All blocks cleared\n")

    print("=" * 50)
    print("All tests passed successfully!")
    print("=" * 50)

    # Cleanup
    try:
        os.remove('test_ham_coordinator.db')
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
        exit(1)
