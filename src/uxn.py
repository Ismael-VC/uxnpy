import ctypes
import os
from typing import Optional
from enum import IntEnum


class UxnMode(IntEnum):
    """Uxn execution mode"""
    CLI = 0  # Headless/console mode (default)
    GUI = 1  # GUI mode with SDL


class Uxn:
    def __init__(self, lib_path: Optional[str] = None, mode: UxnMode = UxnMode.CLI):
        """
        Create a Uxn instance.

        Args:
            lib_path: Path to the Uxn library (auto-detected if None)
            mode: Execution mode (UxnMode.CLI or UxnMode.GUI)
        """
        if lib_path is None:
            lib_path = self._find_library()

        if not os.path.exists(lib_path):
            raise RuntimeError(f"Library not found at: {lib_path}")

        self._lib = ctypes.CDLL(lib_path)
        self._setup_ctypes()

        self._handle = self._lib.uxn_create_with_mode(mode)
        if not self._handle:
            raise RuntimeError("Failed to create Uxn instance")

        self._mode = mode

    def __del__(self):
        if hasattr(self, '_handle') and self._handle:
            self._lib.uxn_destroy(self._handle)

    def _find_library(self):
        lib_name = self._get_lib_name()

        possible_paths = [
            os.path.join(os.path.dirname(__file__), '..', 'build', lib_name),
            os.path.join('build', lib_name),
            os.path.join(os.path.dirname(__file__), lib_name),
        ]

        for path in possible_paths:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                return abs_path

        raise RuntimeError(
            f"Could not find {lib_name}. Searched:\n" +
            "\n".join(f"  - {os.path.abspath(p)}" for p in possible_paths) +
            "\n\nPlease run 'make' to build the library first."
        )

    @staticmethod
    def _get_lib_name():
        import platform
        system = platform.system()
        if system == "Linux":
            return "libuxn.so"
        elif system == "Darwin":
            return "libuxn.dylib"
        elif system == "Windows":
            return "uxn.dll"
        return "libuxn.so"

    def _setup_ctypes(self):
        # Mode enum
        self._lib.uxn_create.argtypes = []
        self._lib.uxn_create.restype = ctypes.c_void_p

        self._lib.uxn_create_with_mode.argtypes = [ctypes.c_int]
        self._lib.uxn_create_with_mode.restype = ctypes.c_void_p

        self._lib.uxn_destroy.argtypes = [ctypes.c_void_p]
        self._lib.uxn_destroy.restype = None

        self._lib.uxn_get_mode.argtypes = [ctypes.c_void_p]
        self._lib.uxn_get_mode.restype = ctypes.c_int

        self._lib.uxn_set_mode.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self._lib.uxn_set_mode.restype = ctypes.c_int

        self._lib.uxn_instance_init.argtypes = [ctypes.c_void_p]
        self._lib.uxn_instance_init.restype = None

        self._lib.uxn_instance_eval.argtypes = [ctypes.c_void_p, ctypes.c_ushort]
        self._lib.uxn_instance_eval.restype = ctypes.c_int

        self._lib.uxn_instance_load_rom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
        self._lib.uxn_instance_load_rom.restype = ctypes.c_int

        self._lib.uxn_instance_console_input.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint]
        self._lib.uxn_instance_console_input.restype = None

        self._lib.uxn_instance_get_ram.argtypes = [ctypes.c_void_p]
        self._lib.uxn_instance_get_ram.restype = ctypes.POINTER(ctypes.c_ubyte)

        self._lib.uxn_instance_get_dev.argtypes = [ctypes.c_void_p]
        self._lib.uxn_instance_get_dev.restype = ctypes.POINTER(ctypes.c_ubyte)

        self._lib.uxn_instance_get_wst_ptr.argtypes = [ctypes.c_void_p]
        self._lib.uxn_instance_get_wst_ptr.restype = ctypes.POINTER(ctypes.c_ubyte)

        self._lib.uxn_instance_get_pc.argtypes = [ctypes.c_void_p]
        self._lib.uxn_instance_get_pc.restype = ctypes.POINTER(ctypes.c_ushort)

        self._lib.uxn_instance_get_rst_ptr.argtypes = [ctypes.c_void_p]
        self._lib.uxn_instance_get_rst_ptr.restype = ctypes.POINTER(ctypes.c_ubyte)

        self._lib.uxn_instance_get_wst.argtypes = [ctypes.c_void_p]
        self._lib.uxn_instance_get_wst.restype = ctypes.POINTER(ctypes.c_ubyte)

        self._lib.uxn_instance_get_rst.argtypes = [ctypes.c_void_p]
        self._lib.uxn_instance_get_rst.restype = ctypes.POINTER(ctypes.c_ubyte)

        self._lib.uxn_instance_set_dev.argtypes = [ctypes.c_void_p, ctypes.c_ubyte, ctypes.c_ubyte]
        self._lib.uxn_instance_set_dev.restype = None

        # GUI-specific functions (if SDL is enabled)
        try:
            self._lib.uxnemu_handle_events.argtypes = [ctypes.c_void_p]
            self._lib.uxnemu_handle_events.restype = ctypes.c_int

            self._lib.uxnemu_redraw.argtypes = [ctypes.c_void_p]
            self._lib.uxnemu_redraw.restype = None

            self._lib.uxnemu_is_running.argtypes = [ctypes.c_void_p]
            self._lib.uxnemu_is_running.restype = ctypes.c_int

            self._has_gui = True
        except AttributeError:
            self._has_gui = False

    @property
    def mode(self) -> UxnMode:
        """Get current execution mode"""
        return UxnMode(self._lib.uxn_get_mode(self._handle))

    @mode.setter
    def mode(self, mode: UxnMode):
        """Set execution mode (CLI or GUI)"""
        if not self._lib.uxn_set_mode(self._handle, mode):
            raise RuntimeError(f"Failed to switch to mode {mode}")
        self._mode = mode

    def load_rom(self, filepath: str) -> bool:
        """Load a ROM file"""
        with open(filepath, 'rb') as f:
            rom_data = f.read()
        return self._lib.uxn_instance_load_rom(self._handle, rom_data, len(rom_data)) == 0

    def eval(self, pc: int = 0x100, run_loop: bool = True) -> int:
        """
        Evaluate/run the Uxn VM.

        In CLI mode: Runs headless execution
        In GUI mode: Initializes the window and runs event loop if run_loop=True

        Args:
            pc: Program counter start address (default 0x100)
            run_loop: In GUI mode, whether to run the main event loop (default True)

        Returns:
            Result code from execution
        """
        # Initial evaluation
        result = self._lib.uxn_instance_eval(self._handle, pc)

        # In GUI mode, run the event loop
        if self.mode == UxnMode.GUI and run_loop and self._has_gui:
            import time

            print("GUI event loop starting...")
            frame_count = 0

            while self.is_running():
                # Check for halt
                if self.dev[0x0f]:
                    print(f"VM halted with code: {self.dev[0x0f]}")
                    break

                # Handle SDL events
                if not self.handle_events():
                    print("Window closed by user")
                    break

                # Evaluate screen vector for frame updates
                screen_vector = (self.dev[0x20] << 8) | self.dev[0x21]
                if screen_vector:
                    self._lib.uxn_instance_eval(self._handle, screen_vector)

                # Redraw
                self.redraw()

                frame_count += 1
                if frame_count % 60 == 0:
                    print(f"Frame: {frame_count}")

                time.sleep(1.0 / 60.0)  # ~60 FPS

            print(f"GUI event loop ended after {frame_count} frames")

        return result

    def console_input(self, c: int, input_type: int):
        """Send console input to the VM"""
        self._lib.uxn_instance_console_input(self._handle, c, input_type)

    # GUI-specific methods
    def handle_events(self) -> bool:
        """
        Handle GUI events (only in GUI mode).
        Returns False if window should close.
        """
        if self.mode != UxnMode.GUI or not self._has_gui:
            return True
        return bool(self._lib.uxnemu_handle_events(self._handle))

    def redraw(self):
        """Redraw the GUI window (only in GUI mode)"""
        if self.mode != UxnMode.GUI or not self._has_gui:
            return
        self._lib.uxnemu_redraw(self._handle)

    def is_running(self) -> bool:
        """Check if GUI is still running (only in GUI mode)"""
        if self.mode != UxnMode.GUI or not self._has_gui:
            return False
        return bool(self._lib.uxnemu_is_running(self._handle))

    @property
    def ram(self):
        ptr = self._lib.uxn_instance_get_ram(self._handle)
        return ctypes.cast(ptr, ctypes.POINTER(ctypes.c_ubyte * (0x10000*0x10))).contents

    @property
    def pc(self):
        ptr = self._lib.uxn_instance_get_pc(self._handle)
        return ptr[0]

    @pc.setter
    def pc(self, value: int):
        ptr = self._lib.uxn_instance_get_pc(self._handle)
        ptr[0] = value & 0xFFFF

    @property
    def dev(self):
        ptr = self._lib.uxn_instance_get_dev(self._handle)
        return ctypes.cast(ptr, ctypes.POINTER(ctypes.c_ubyte * 0x100)).contents

    @property
    def wst(self):
        ptr = self._lib.uxn_instance_get_wst(self._handle)
        return ctypes.cast(ptr, ctypes.POINTER(ctypes.c_ubyte * 0x100)).contents

    @property
    def rst(self):
        ptr = self._lib.uxn_instance_get_rst(self._handle)
        return ctypes.cast(ptr, ctypes.POINTER(ctypes.c_ubyte * 0x100)).contents

    @property
    def wsp(self):
        ptr = self._lib.uxn_instance_get_wst_ptr(self._handle)
        return ptr[0]

    @wsp.setter
    def wsp(self, value: int):
        ptr = self._lib.uxn_instance_get_wst_ptr(self._handle)
        ptr[0] = value & 0xFF

    @property
    def rsp(self):
        ptr = self._lib.uxn_instance_get_rst_ptr(self._handle)
        return ptr[0]

    @rsp.setter
    def rsp(self, value: int):
        ptr = self._lib.uxn_instance_get_rst_ptr(self._handle)
        ptr[0] = value & 0xFF

    def deo(self, port: int, value: int):
        """Write to device port"""
        self._lib.uxn_instance_set_dev(self._handle, port & 0xFF, value & 0xFF)

    def dei(self, port: int) -> int:
        """Read from device port"""
        return self.dev[port & 0xFF]

    def reset(self):
        """Reset the VM"""
        self._lib.uxn_instance_init(self._handle)

    def run_rom(self, filepath: str, args: list = None) -> int:
        """
        Load and run a ROM file.

        Args:
            filepath: Path to the ROM file
            args: Command-line arguments to pass to the ROM

        Returns:
            Exit code
        """
        if not self.load_rom(filepath):
            raise RuntimeError(f"Failed to load ROM: {filepath}")

        self.deo(0x17, 1 if args else 0)

        if not self.eval(0x100):
            return self.dev[0x0f] & 0x7f

        console_vector = (self.dev[0x10] << 8) | self.dev[0x11]

        if console_vector and args:
            for i, arg in enumerate(args):
                for c in arg:
                    if self.dev[0x0f]:
                        break
                    self.console_input(ord(c), 2)
                self.console_input(0, 3 if i < len(args) - 1 else 4)

        return self.dev[0x0f] & 0x7f

    def dump(self):
        """Dump VM state for debugging"""
        console_vector = (self.dev[0x10] << 8) | self.dev[0x11]

        print(f"Mode:                  {self.mode.name}")
        print(f"Program Counter:       0x{self.pc:04x}")
        print(f"Working Stack Pointer: 0x{self.wsp:02x}")
        print(f"Return Stack Pointer:  0x{self.rsp:02x}")
        print(f"Console Vector:        0x{console_vector:04x}")
        print(f"Exit Code:             0x{self.dev[0x0f]:02x}")

        if self.wsp > 0:
            print(f"\nWorking Stack (top {min(8, self.wsp)} items):")
            for i in range(min(8, self.wsp)):
                print(f"  [{i}] = 0x{self.wst[i]:02x}")

        if self.rsp > 0:
            print(f"\nReturn Stack (top {min(8, self.rsp)} items):")
            for i in range(min(8, self.rsp)):
                print(f"  [{i}] = 0x{self.rst[i]:02x}")


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python uxn.py <rom_file> [--gui]")
        sys.exit(1)

    rom_file = sys.argv[1]
    use_gui = "--gui" in sys.argv

    if use_gui:
        print(f"=== Running {rom_file} in GUI Mode ===")
        uxn = Uxn(mode=UxnMode.GUI)
        uxn.load_rom(rom_file)
        print("Window should appear... Press ESC or close window to exit")
        uxn.eval()  # This will run the event loop
    else:
        print(f"=== Running {rom_file} in CLI Mode ===")
        uxn = Uxn(mode=UxnMode.CLI)
        uxn.load_rom(rom_file)
        result = uxn.eval()
        print(f"Exit code: {result}")

    print("Done!")
