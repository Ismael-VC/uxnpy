from typing import Optional, List
import base64
import sys
from .uxn import Uxn
from .devices.console import Console, peek16, poke16

def b64encode(bs: bytes) -> str:
    """
    Encode bytes to a URL-safe base64 string.
    >>> b64encode(b'\\x12\\x34')
    'EjQ'
    """
    encoded = base64.b64encode(bs).decode('ascii')
    return encoded.replace('/', '_').replace('+', '-').rstrip('=')

def b64decode(s: str) -> bytearray:
    """
    Decode a URL-safe base64 string to bytes.
    >>> b64decode('EjQ')
    bytearray(b'\\x12\\x34')
    """
    s = s.replace('_', '/').replace('-', '+')
    s += '=' * (4 - len(s) % 4 if len(s) % 4 else 0)
    return bytearray(base64.b64decode(s))

def decodeUlz(src: bytearray) -> bytearray:
    """
    Decompress a ULZ-compressed bytearray.
    >>> src = bytearray([0x01, 0x41, 0x80, 0x00])
    >>> decodeUlz(src)
    bytearray(b'AA')
    """
    dst = []
    sp = 0
    while sp < len(src):
        c = src[sp]
        sp += 1
        if c & 0x80:
            if c & 0x40:
                if sp >= len(src):
                    raise ValueError("incomplete CPY2")
                length = ((c & 0x3f) << 8) | src[sp]
                sp += 1
            else:
                length = c & 0x3f
            if sp >= len(src):
                raise ValueError("incomplete CPY")
            cp = len(dst) - (src[sp] + 1)
            sp += 1
            if cp < 0:
                raise ValueError("CPY underflow")
            for _ in range(length + 4):
                dst.append(dst[cp])
                cp += 1
        else:
            if sp + c >= len(src):
                raise ValueError(f"LIT out of bounds: {sp} + {c} >= {len(src)}")
            for _ in range(c + 1):
                dst.append(src[sp])
                sp += 1
    return bytearray(dst)

def encodeUlz(src: bytearray) -> bytearray:
    """
    Compress a bytearray using ULZ compression.
    >>> encodeUlz(bytearray(b'AA'))
    bytearray(b'\\x01A\\x80\\x00')
    """
    MIN_MAX_LENGTH = 4
    dst = []
    sp = 0
    litp = -1
    while sp < len(src):
        dlen = min(sp, 256)
        slen = min(len(src) - sp, 0x3fff + MIN_MAX_LENGTH)
        bmp, bmlen = 0, 0
        dp = sp - dlen
        for i in range(dlen):
            j = 0
            while j < slen and src[sp + j] == src[dp + (j % dlen)]:
                j += 1
            if j > bmlen:
                bmlen = j
                bmp = dp
            dp += 1
        if bmlen >= MIN_MAX_LENGTH:
            bmctl = bmlen - MIN_MAX_LENGTH
            if bmctl > 0x3f:
                dst.append((bmctl >> 8) | 0xc0)
                dst.append(bmctl & 0xff)
            else:
                dst.append(bmctl | 0x80)
            dst.append(sp - bmp - 1)
            sp += bmlen
            litp = -1
        else:
            if litp >= 0:
                dst[litp] = (dst[litp] + 1) & 0xff
                if dst[litp] == 127:
                    litp = -1
            else:
                dst.append(0)
                litp = len(dst) - 1
            dst.append(src[sp])
            sp += 1
    return bytearray(dst)

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
        """
        Load a ROM into the Uxn VM and evaluate it.
        >>> e = Emu()
        >>> e.load(bytearray([0xa0, 0x2a, 0x18, 0x17]))
        *
        >>> e.uxn.wst.ptr
        0
        """
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
        """
        Device output: write to a device port.
        >>> import sys
        >>> from io import StringIO
        >>> e = Emu()
        >>> old_stdout = sys.stdout
        >>> sys.stdout = StringIO()
        >>> e.deo(0x18, 42)
        >>> sys.stdout.getvalue()
        '*'
        >>> sys.stdout = old_stdout
        >>> e = Emu(capture_output=True)
        >>> e.deo(0x18, 42)
        >>> e.console.output_buffer
        bytearray(b'*')
        """
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