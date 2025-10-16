import logging
from typing import Optional, List
import base64
import sys
from .uxn import Uxn
from .devices.console import Console, peek16, poke16


logger = logging.getLogger(__name__)

class Emu:
    """
    Main emulator class for the Uxn virtual machine with a CLI interface.
    >>> e = Emu()
    >>> e.load(bytearray([0xa0, 0x2a, 0x18, 0x17]))
    *
    >>> e.uxn.wst.ptr
    0
    """
    def __init__(self, app: Optional[object] = None, capture_output: bool = False) -> None:
        """
        Initialize the emulator with a Uxn VM and Console device.
        :param app: Optional Textual app for console output redirection.
        :param capture_output: If True, Console captures output in a bytearray.
        >>> e = Emu(capture_output=True)
        >>> e.load(bytearray([0xa0, 0x2a, 0x18, 0x17]))
        >>> e.console.output_buffer
        bytearray(b'*')
        """
        self.app: Optional[object] = app
        self.uxn: Uxn = Uxn(self)
        self.console: Console = Console(self.uxn, app=app, capture_output=capture_output)
        self.system: Optional[object] = None
        self.controller: Optional[object] = None
        self.screen: Optional[object] = None
        self.datetime: Optional[object] = None
        self.mouse: Optional[object] = None

    def init(self) -> None:
        """
        Initialize the emulator and its devices.
        >>> e = Emu()
        >>> e.init()
        >>> isinstance(e.console, Console)
        True
        """
        self.console.init()
        self.update_repr()

    def load_file(self, file_path: str) -> None:
        """
        Load a ROM from a file path.
        >>> import tempfile
        >>> with tempfile.NamedTemporaryFile(delete=False) as f:
        ...     f.write(b'\\xa0\\x2a\\x18\\x17')
        ...     f.flush()
        ...     e = Emu()
        ...     e.load_file(f.name)
        ...     e.uxn.wst.ptr
        *
        4
        0
        >>> import os
        >>> os.unlink(f.name)
        """
        with open(file_path, 'rb') as f:
            rom = bytearray(f.read())
        self.load(rom)

    def load(self, rom: bytearray, from_url: bool = False) -> None:
        logger.debug(f"Loading ROM of length {len(rom)}")
        self.uxn.load(rom).eval(0x0100)
        self.update_repr()

    def dei(self, port: int) -> int:
        """
        Device input: read from a device port.
        >>> e = Emu()
        >>> e.uxn.dev[0x10] = 0x42
        >>> e.dei(0x10)
        66
        """
        if (port & 0xf0) == 0xc0 and self.datetime:
            return self.datetime.dei(port)
        elif (port & 0xf0) == 0x20 and self.screen:
            return self.screen.dei(port)
        return self.uxn.dev[port]

    def deo(self, port: int, val: int) -> None:
        logger.debug(f"DEO: port={port:02x}, val={val:02x}")
        self.uxn.dev[port] = val
        if (port & 0xf0) == 0x00 and self.system:
            self.system.deo(port)
        elif (port & 0xf0) == 0x10:
            self.console.deo(port)
            self.update_repr()
        elif (port & 0xf0) == 0x20 and self.screen:
            self.screen.deo(port)

    def update_repr(self) -> None:
        """
        Update the Textual app with the current Uxn state if an app is attached.
        >>> e = Emu()
        >>> e.update_repr()  # No crash if app is None
        """
        if self.app:
            self.app.update_repr()