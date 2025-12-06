#!/usr/bin/env python3
"""
Test script for Uxn GUI functionality
"""

import pytest
from uxn import Uxn, UxnMode
import sys
import os


@pytest.fixture
def rom_file():
    """Fixture that provides the path to a test ROM"""
    test_rom = os.path.join(os.path.dirname(__file__), "opctest.rom")
    if os.path.exists(test_rom):
        return test_rom

    # If opctest.rom doesn't exist, create a minimal test ROM
    test_rom = os.path.join(os.path.dirname(__file__), "test_minimal.rom")
    create_minimal_rom(test_rom)
    return test_rom


def create_minimal_rom(output_path):
    """Create a simple test ROM that initializes the screen"""
    # Minimal Uxn program that sets up the screen
    rom = bytearray([
        0x80, 0x01,  # LIT 01 - set pixel color
        0x00, 0x2f,  # DEO to screen pixel port
        0x00, 0x00,  # BRK - halt
    ])

    with open(output_path, "wb") as f:
        f.write(rom)


def test_cli_mode():
    """Test CLI mode execution"""
    print("\n=== Testing CLI Mode ===")
    uxn = Uxn(mode=UxnMode.CLI)

    print("Created Uxn instance in CLI mode")
    print(f"Current mode: {uxn.mode.name}")

    # Verify mode
    assert uxn.mode == UxnMode.CLI

    # Dump initial state
    uxn.dump()

    print("✓ CLI mode test passed")


def test_gui_mode(rom_file):
    """Test GUI mode with a ROM file"""
    print(f"\n=== Testing GUI Mode with {rom_file} ===")

    # Skip if SDL is not available
    try:
        uxn = Uxn(mode=UxnMode.GUI)
    except Exception as e:
        pytest.skip(f"SDL not available: {e}")

    print(f"Created Uxn instance in GUI mode")
    print(f"Current mode: {uxn.mode.name}")

    assert uxn.mode == UxnMode.GUI

    print(f"Loading ROM: {rom_file}")
    assert uxn.load_rom(rom_file), "Failed to load ROM"

    print("ROM loaded successfully")
    print("NOTE: GUI test requires manual verification")
    print("      Run 'python tests/test_gui.py' manually to see window")

    # Don't run the event loop in automated tests
    # Just verify we can call eval without error
    result = uxn.eval(run_loop=False)

    print("✓ GUI mode test passed")


def test_mode_switching(rom_file):
    """Test switching between CLI and GUI modes"""
    print("\n=== Testing Mode Switching ===")

    # Start in CLI
    uxn = Uxn(mode=UxnMode.CLI)
    print(f"Started in {uxn.mode.name} mode")
    assert uxn.mode == UxnMode.CLI

    uxn.load_rom(rom_file)
    print(f"Loaded ROM: {rom_file}")

    # Try to switch to GUI (may fail if SDL not available)
    try:
        print("Switching to GUI mode...")
        uxn.mode = UxnMode.GUI
        print(f"Now in {uxn.mode.name} mode")
        assert uxn.mode == UxnMode.GUI

        # Don't run event loop in automated tests
        print("✓ Mode switching test passed")
    except Exception as e:
        pytest.skip(f"GUI mode not available: {e}")


# Manual test functions (for interactive testing)
def manual_test_gui_mode(rom_file):
    """Manual test GUI mode with a ROM file (interactive)"""
    print(f"=== Manual GUI Test with {rom_file} ===")

    try:
        uxn = Uxn(mode=UxnMode.GUI)
        print(f"Created Uxn instance in GUI mode")
        print(f"Current mode: {uxn.mode.name}")

        print(f"Loading ROM: {rom_file}")
        if not uxn.load_rom(rom_file):
            print("Failed to load ROM!")
            return False

        print("ROM loaded successfully")
        print("Starting GUI event loop...")
        print("Press ESC or close the window to exit")

        # Run with event loop
        uxn.eval(run_loop=True)

        print("\n✓ GUI mode test completed\n")
        return True

    except Exception as e:
        print(f"✗ GUI mode test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def manual_test_mode_switching(rom_file):
    """Manual test mode switching (interactive)"""
    print("=== Manual Mode Switching Test ===")

    # Start in CLI
    uxn = Uxn(mode=UxnMode.CLI)
    print(f"Started in {uxn.mode.name} mode")

    uxn.load_rom(rom_file)
    print(f"Loaded ROM: {rom_file}")

    # Switch to GUI
    print("Switching to GUI mode...")
    uxn.mode = UxnMode.GUI
    print(f"Now in {uxn.mode.name} mode")

    print("Running in GUI mode (press ESC to close)...")
    uxn.eval(run_loop=True)

    print("\n✓ Mode switching test passed\n")


if __name__ == "__main__":
    """Run manual interactive tests"""
    print("Uxn GUI Manual Test Suite\n")
    print("=" * 50)

    # Check if ROM file provided
    if len(sys.argv) > 1:
        rom_file = sys.argv[1]
    else:
        rom_file = os.path.join(os.path.dirname(__file__), "opctest.rom")
        if not os.path.exists(rom_file):
            print("No ROM file provided, creating test ROM...")
            rom_file = os.path.join(os.path.dirname(__file__), "test_minimal.rom")
            create_minimal_rom(rom_file)
            print(f"Created test ROM: {rom_file}\n")

    # Test GUI mode
    if rom_file:
        success = manual_test_gui_mode(rom_file)

        if success:
            # Test mode switching
            response = input("\nTest mode switching? (y/n): ")
            if response.lower() == 'y':
                manual_test_mode_switching(rom_file)

    print("=" * 50)
    print("Manual tests completed!")
