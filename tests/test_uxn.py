"""
Tests for PyUxn wrapper
"""

import pytest
import sys
import os

# Add src to path if needed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from uxn import Uxn
except ImportError:
    pytest.skip("Uxn not available", allow_module_level=True)


class TestUxn:
    """Test suite for Uxn wrapper"""

    def test_uxn_initialization(self):
        """Test VM can be initialized"""
        uxn = Uxn()
        assert uxn is not None

    def test_memory_access(self):
        """Test RAM access"""
        uxn = Uxn()

        # Write and read
        uxn.ram[0x100] = 0x42
        assert uxn.ram[0x100] == 0x42

        # Test boundary
        uxn.ram[0] = 0xFF
        assert uxn.ram[0] == 0xFF

        uxn.ram[0xFFFF] = 0xAA
        assert uxn.ram[0xFFFF] == 0xAA

    def test_device_access(self):
        """Test device memory access"""
        uxn = Uxn()

        uxn.deo(0x18, 0x41)
        assert uxn.dei(0x18) == 0x41

        # Test console device
        uxn.deo(0x12, ord('A'))
        assert uxn.dei(0x12) == ord('A')

    def test_stack_pointers(self):
        """Test stack pointer access"""
        uxn = Uxn()

        # Initially zero
        assert uxn.wsp == 0
        assert uxn.rsp == 0

        # Can be set
        uxn.wsp = 5
        assert uxn.wsp == 5

        uxn.rsp = 3
        assert uxn.rsp == 3

    def test_stack_access(self):
        """Test direct stack access"""
        uxn = Uxn()

        # Write to working stack
        uxn.wst[0] = 0x42
        assert uxn.wst[0] == 0x42

        # Write to return stack
        uxn.rst[0] = 0x99
        assert uxn.rst[0] == 0x99

    def test_reset(self):
        """Test VM reset"""
        uxn = Uxn()

        # Modify state
        uxn.ram[0x100] = 0x42
        uxn.deo(0x10, 0x99)
        uxn.wsp = 5

        # Reset
        uxn.reset()

        # Memory should be cleared
        assert uxn.ram[0x100] == 0
        assert uxn.dev[0x10] == 0
        assert uxn.wsp == 0

    def test_simple_program(self):
        """Test executing a simple program"""
        uxn = Uxn()

        # Simple program: LIT 0x42, BRK
        uxn.ram[0x100] = 0x80  # LIT
        uxn.ram[0x101] = 0x42  # value
        uxn.ram[0x102] = 0x00  # BRK

        # Execute
        result = uxn.eval(0x100)
        assert result == 1  # Should return 1 (success)

        # Check stack
        assert uxn.wsp == 1
        assert uxn.wst[0] == 0x42

    def test_load_rom_nonexistent(self):
        """Test loading non-existent ROM file"""
        uxn = Uxn()

        with pytest.raises(FileNotFoundError):
            uxn.load_rom('nonexistent_file.rom')

    def test_arithmetic_operations(self):
        """Test basic arithmetic operations"""
        uxn = Uxn()

        # Program: LIT 5, LIT 3, ADD, BRK
        program = [
            0x80, 0x05,  # LIT 5
            0x80, 0x03,  # LIT 3
            0x18,        # ADD
            0x00,        # BRK
        ]

        for i, byte in enumerate(program):
            uxn.ram[0x100 + i] = byte

        result = uxn.eval(0x100)
        assert result == 1

        # Result should be 8 on top of stack
        assert uxn.wsp == 1
        assert uxn.wst[0] == 8

    def test_stack_operations(self):
        """Test stack manipulation operations"""
        uxn = Uxn()

        # Program: LIT 0x42, DUP, BRK
        program = [
            0x80, 0x42,  # LIT 0x42
            0x06,        # DUP
            0x00,        # BRK
        ]

        for i, byte in enumerate(program):
            uxn.ram[0x100 + i] = byte

        result = uxn.eval(0x100)
        assert result == 1

        # Should have two values on stack
        assert uxn.wsp == 2
        assert uxn.wst[0] == 0x42
        assert uxn.wst[1] == 0x42


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_stack_underflow(self):
        """Test behavior with stack underflow"""
        uxn = Uxn()

        # Try to pop from empty stack (ADD with no values)
        uxn.ram[0x100] = 0x18  # ADD
        uxn.ram[0x101] = 0x00  # BRK

        # This should not crash
        result = uxn.eval(0x100)
        # Behavior is undefined but shouldn't crash
        assert result in [0, 1]

    def test_division_by_zero(self):
        """Test division by zero handling"""
        uxn = Uxn()

        # Program: LIT 5, LIT 0, DIV, BRK
        program = [
            0x80, 0x05,  # LIT 5
            0x80, 0x00,  # LIT 0
            0x1b,        # DIV
            0x00,        # BRK
        ]

        for i, byte in enumerate(program):
            uxn.ram[0x100 + i] = byte

        result = uxn.eval(0x100)
        assert result == 1

        # Result should be 0 (defined behavior for div by zero)
        assert uxn.wst[0] == 0

    def test_memory_wrap(self):
        """Test memory boundary wrapping"""
        uxn = Uxn()

        # Access last byte
        uxn.ram[0xFFFF] = 0xFF
        assert uxn.ram[0xFFFF] == 0xFF

        # First byte
        uxn.ram[0x0000] = 0x00
        assert uxn.ram[0x0000] == 0x00


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
