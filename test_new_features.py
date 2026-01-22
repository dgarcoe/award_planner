#!/usr/bin/env python3
"""Test script for new features: one block per operator, Galician translations, admin unblock."""
import os
import gc

# Use a test database - MUST be set before importing database module
os.environ['DATABASE_PATH'] = 'test_new_features.db'

import database as db
from translations import get_text, AVAILABLE_LANGUAGES

def wait_for_db():
    """Small delay to ensure DB operations complete."""
    gc.collect()

def run_tests():
    print("Starting new features tests...\n")

    # Initialize database
    print("1. Initializing database...")
    db.init_database()
    print("✓ Database initialized\n")

    # Test operator creation
    print("2. Creating test operators...")
    db.create_operator("W1ABC", "John Doe", "password123", is_admin=False)
    db.create_operator("W1XYZ", "Jane Smith", "password456", is_admin=True)
    print("✓ Test operators created\n")

    # Test one block per operator - first block
    print("3. Testing one block per operator - first block...")
    wait_for_db()
    success, message = db.block_band_mode("W1ABC", "20m", "SSB")
    assert success, f"Failed to block: {message}"
    assert "previous" not in message.lower(), "Should not mention previous block on first block"
    print(f"✓ First block successful: {message}\n")

    # Test one block per operator - second block (should auto-release first)
    print("4. Testing one block per operator - auto-release previous...")
    wait_for_db()
    success, message = db.block_band_mode("W1ABC", "40m", "CW")
    assert success, f"Failed to block: {message}"
    assert "previous" in message.lower(), "Should mention previous block was released"
    assert "20m" in message and "SSB" in message, "Should mention which block was released"
    print(f"✓ Second block with auto-release: {message}\n")

    # Verify only one block exists for operator
    print("5. Verifying only one block per operator...")
    wait_for_db()
    blocks = db.get_operator_blocks("W1ABC")
    assert len(blocks) == 1, f"Expected 1 block, got {len(blocks)}"
    assert blocks[0]['band'] == "40m" and blocks[0]['mode'] == "CW", "Wrong block remained"
    print(f"✓ Only one block exists: {blocks[0]['band']}/{blocks[0]['mode']}\n")

    # Test unblock_all_for_operator
    print("6. Testing unblock_all_for_operator...")
    wait_for_db()
    # Add another operator with a block
    db.block_band_mode("W1XYZ", "15m", "FT8")
    success, message, count = db.unblock_all_for_operator("W1ABC")
    assert success, f"Failed to unblock all: {message}"
    assert count == 1, f"Expected to release 1 block, got {count}"
    print(f"✓ Unblocked all: {message}\n")

    # Verify blocks were released
    print("7. Verifying blocks were released...")
    wait_for_db()
    blocks = db.get_operator_blocks("W1ABC")
    assert len(blocks) == 0, f"Expected 0 blocks, got {len(blocks)}"
    # W1XYZ block should still exist
    blocks_xyz = db.get_operator_blocks("W1XYZ")
    assert len(blocks_xyz) == 1, "W1XYZ block should still exist"
    print("✓ Blocks correctly released\n")

    # Test admin_unblock_band_mode
    print("8. Testing admin_unblock_band_mode...")
    wait_for_db()
    success, message = db.admin_unblock_band_mode("15m", "FT8")
    assert success, f"Failed to admin unblock: {message}"
    assert "W1XYZ" in message, "Should mention who was blocking"
    print(f"✓ Admin unblock successful: {message}\n")

    # Verify admin unblock worked
    print("9. Verifying admin unblock...")
    wait_for_db()
    blocks_xyz = db.get_operator_blocks("W1XYZ")
    assert len(blocks_xyz) == 0, "Block should be released"
    print("✓ Admin unblock verified\n")

    # Test Galician translations
    print("10. Testing Galician translations...")
    gl_title = get_text('app_title', 'gl')
    assert gl_title == "Coordinador de Premios de Radio Afeccionados", f"Unexpected Galician title: {gl_title}"
    gl_welcome = get_text('welcome', 'gl')
    assert gl_welcome == "Benvido", f"Unexpected Galician welcome: {gl_welcome}"
    print(f"✓ Galician translations working: title='{gl_title[:30]}...'\n")

    # Test all three languages are available
    print("11. Testing all available languages...")
    assert 'en' in AVAILABLE_LANGUAGES, "English missing"
    assert 'es' in AVAILABLE_LANGUAGES, "Spanish missing"
    assert 'gl' in AVAILABLE_LANGUAGES, "Galician missing"
    assert AVAILABLE_LANGUAGES['gl'] == 'Galego', "Galician name incorrect"
    print(f"✓ All 3 languages available: {', '.join(AVAILABLE_LANGUAGES.values())}\n")

    # Test admin block management translations
    print("12. Testing admin block management translations...")
    en_manage = get_text('manage_all_blocks', 'en')
    es_manage = get_text('manage_all_blocks', 'es')
    gl_manage = get_text('manage_all_blocks', 'gl')
    assert en_manage == "Manage All Blocks", f"English translation wrong: {en_manage}"
    assert es_manage == "Gestionar Todos los Bloqueos", f"Spanish translation wrong: {es_manage}"
    assert gl_manage == "Xestionar Todos os Bloqueos", f"Galician translation wrong: {gl_manage}"
    print("✓ Admin block management translations verified\n")

    # Test timeline translations
    print("13. Testing timeline translations...")
    en_timeline = get_text('tab_timeline', 'en')
    es_timeline = get_text('tab_timeline', 'es')
    gl_timeline = get_text('tab_timeline', 'gl')
    assert en_timeline == "Timeline", f"English timeline wrong: {en_timeline}"
    assert es_timeline == "Línea Temporal", f"Spanish timeline wrong: {es_timeline}"
    assert gl_timeline == "Liña Temporal", f"Galician timeline wrong: {gl_timeline}"
    print("✓ Timeline translations verified\n")

    print("=" * 50)
    print("All new features tests passed successfully!")
    print("=" * 50)

    # Cleanup
    try:
        os.remove('test_new_features.db')
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
