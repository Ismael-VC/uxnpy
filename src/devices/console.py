from typing import Optional
import sys
from io import StringIO
from ..uxn import Uxn

def peek16(dev: bytearray, addr: int) -> int:
    """
    Read a 16-bit value from the device memory at addr.
    >>> dev = bytearray(256)
    >>> dev[0x10] = 0x12
    >>> dev[0x11] = 0x34
    >>> peek16(dev, 0x10)
    4660
    """
    return (dev[addr] << 8) | dev[addr + 1]

def poke16(mem: bytearray, addr: int, val: int) -> None:
    """
    Write a 16-bit value to memory at the specified address.
    >>> mem = bytearray(256)
    >>> poke16(mem, 0x10, 0x1234)
    >>> mem[0x10]
    18
    >>> mem[0x11]
    52
    """
    mem[addr] = (val >> 8) & 0xff
    mem[addr + 1] = val & 0xff

class Console:
    """
    Console device emulator for the Uxn virtual machine.
    >>> u = Uxn()
    >>> c = Console(u)
    >>> c.output(65)
    A
    >>> c.error(66)
    B
    """
    def __init__(self, uxn: Uxn, app: Optional[object] = None, capture_output: bool = False) -> None:
        """
        Initialize the Console device.
        :param uxn: The Uxn virtual machine instance.
        :param app: Optional Textual app for output redirection.
        :param capture_output: If True, store stdout in output_buffer and stderr in error_buffer.
        """
        self.uxn = uxn
        self.app = app
        self.input_buffer = ""
        self.capture_output = capture_output
        self.output_buffer = bytearray() if capture_output else None
        self.error_buffer = bytearray() if capture_output else None

    def init(self) -> None:
        """
        Initialize the console device (no-op for standard I/O).
        >>> c = Console(Uxn())
        >>> c.init()
        >>> c.input_buffer
        ''
        """
        pass

    def deo(self, addr: int) -> None:
        """
        Handle device output to console ports (0x18 for stdout, 0x19 for stderr).
        >>> from unittest.mock import Mock
        >>> u = Uxn()
        >>> app = Mock()
        >>> c = Console(u, app=app)
        >>> u.dev[0x18] = 42
        >>> c.deo(0x18)
        >>> app.write_output.assert_called_with('*')
        >>> c = Console(u, capture_output=True)
        >>> u.dev[0x18] = 65
        >>> c.deo(0x18)
        >>> c.output_buffer
        bytearray(b'A')
        >>> u.dev[0x19] = 66
        >>> c.deo(0x19)
        >>> c.error_buffer
        bytearray(b'B')
        """
        if addr == 0x18:
            self.output(self.uxn.dev[0x18])
        elif addr == 0x19:
            self.error(self.uxn.dev[0x19])
        if self.app:
            self.app.update_repr()

    def on_console(self, query: str) -> None:
        """
        Process a line of input, sending each character to the VM.
        >>> u = Uxn()
        >>> c = Console(u)
        >>> c.on_console("hi")
        >>> u.dev[0x12]
        10
        >>> u.dev[0x17]
        1
        """
        for char in query:
            self.input(ord(char), 1)
        self.input(0x0a, 1)
        if self.app:
            self.app.update_repr()

    def output(self, char: int) -> None:
        """
        Output a character to stdout, Textual app, or output_buffer.
        >>> c = Console(Uxn())
        >>> old_stdout = sys.stdout
        >>> sys.stdout = StringIO()
        >>> c.output(65)
        >>> sys.stdout.getvalue()
        'A'
        >>> sys.stdout = old_stdout
        >>> c = Console(Uxn(), capture_output=True)
        >>> c.output(65)
        >>> c.output_buffer
        bytearray(b'A')
        """
        if self.capture_output:
            self.output_buffer.append(char)
        elif self.app:
            self.app.write_output(chr(char))
        else:
            print(chr(char), end='', flush=True)

    def error(self, char: int) -> None:
        """
        Output a character to stderr, Textual app, or error_buffer.
        >>> c = Console(Uxn())
        >>> old_stderr = sys.stderr
        >>> sys.stderr = StringIO()
        >>> c.error(66)
        >>> sys.stderr.getvalue()
        'B'
        >>> sys.stderr = old_stderr
        >>> c = Console(Uxn(), capture_output=True)
        >>> c.error(66)
        >>> c.error_buffer
        bytearray(b'B')
        """
        if self.capture_output:
            self.error_buffer.append(char)
        elif self.app:
            self.app.write_output(f"[red]Error: {chr(char)}[/red]")
        else:
            print(chr(char), end='', flush=True, file=sys.stderr)

    def input(self, char: int, type_: int) -> None:
        """
        Send a character to the Uxn VM and trigger evaluation.
        >>> u = Uxn()
        >>> c = Console(u)
        >>> u.dev[0x10] = 0x01
        >>> u.dev[0x11] = 0x00
        >>> c.input(65, 1)
        >>> u.dev[0x12]
        65
        >>> u.dev[0x17]
        1
        """
        vec = peek16(self.uxn.dev, 0x10)
        self.uxn.dev[0x12] = char & 0xff
        self.uxn.dev[0x17] = type_ & 0xff
        if vec:
            self.uxn.eval(vec)