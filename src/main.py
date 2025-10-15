# src/main.py
import logging
from textual.app import App, ComposeResult
from textual.widgets import RichLog, Input, Static, Footer
from .emu import Emu
from .devices.console import Console
import sys

# Configure logging to file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tui_debug.log', mode='w'),  # Overwrites each run
        logging.StreamHandler(sys.stderr)  # Optional console output
    ]
)
logger = logging.getLogger(__name__)

class UxnApp(App):
    CSS = """
    RichLog#output {
        height: 60%;
        border: tall white;
        margin: 1;
        background: black;
        min-height: 10;
    }
    Input {
        height: 10%;
        margin: 1;
        &:focus {
            border: heavy green;  # Visual feedback for focus
        }
    }
    Static#repr {
        height: 25%;
        border: round green;
        padding: 1;
        background: darkblue;
        content-align: center middle;
        min-height: 4;
    }
    Footer {
        height: 5%;
    }
    """

    def compose(self) -> ComposeResult:
        yield RichLog(id="output")
        yield Input(placeholder="Enter Uxntal source code")
        yield Static(id="repr", classes="repr")
        yield Footer()

    def on_mount(self) -> None:
        logger.info("TUI starting...")
        self.emu = Emu(app=self)  # Primary emulator for debugging
        self.emu.init()
        # Load initial ROM to output '*'
        self.emu.load(bytearray([0xa0, 0x2a, 0x18, 0x17]))
        # Initialize assembler emulator
        self.assembler = Emu(capture_output=True)  # Secondary emulator for assembling
        self.assembler.init()
        # Load drifloon.rom (assembler)
        with open("bin/drifloon.rom", "rb") as f:
            assembler_rom = bytearray(f.read())
        self.assembler.load(assembler_rom)
        # Set input focus and log
        self.query_one(Input).focus()
        logger.debug("Input widget focused")
        self.update_repr()

    def write_output(self, char: str) -> None:
        logger.debug(f"Writing to RichLog: {char}")
        self.query_one(RichLog).write(char)

    def update_repr(self) -> None:
        logger.debug("Updating repr widget")
        self.query_one("#repr", Static).update(str(self.emu.uxn))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        logger.debug(f"Input submitted: {event.value}")
        uxntal_code = event.value
        # Clear assembler's buffers
        self.assembler.console.output_buffer = bytearray()
        self.assembler.console.error_buffer = bytearray()
        # Send Uxntal code to assembler
        self.assembler.console.on_console(uxntal_code)
        # Set input vector and force evaluation
        poke16(self.assembler.uxn.dev, 0x10, 0x0100)
        self.assembler.uxn.eval(0x0100)
        # Get status message (stderr) and assembled ROM (stdout)
        status_message = self.assembler.console.error_buffer.decode('ascii', errors='ignore')
        assembled_rom = self.assembler.console.output_buffer
        # Debug: Log buffer contents and assembler state
        logger.debug(f"Output Buffer (ROM): {assembled_rom.hex()}")
        logger.debug(f"Error Buffer (Status): {status_message}")
        logger.debug(f"Assembler Dev[0x18]: {self.assembler.uxn.dev[0x18]:02x}, Dev[0x19]: {self.assembler.uxn.dev[0x19]:02x}")
        # Write to RichLog
        self.query_one(RichLog).write(f"Input Uxntal:\n{uxntal_code}\n")
        self.query_one(RichLog).write(f"Assembler: {status_message}\n")
        self.query_one(RichLog).write(f"Assembled ROM: {assembled_rom.hex()}\n")
        # Load assembled ROM into primary emulator
        if assembled_rom:
            logger.info(f"Loading assembled ROM into primary Emu: {assembled_rom.hex()}")
            self.emu.load(assembled_rom)
        else:
            logger.warning("No assembled ROM produced")
        # Refocus input to ensure next input works
        self.query_one(Input).focus()
        self.update_repr()

    # Add key event logging to diagnose input issues
    def on_key(self, event) -> None:
        logger.debug(f"Key event: {event.key} (pressed: {event.is_pressed})")
        if event.key == "escape":
            self.app.exit()

if __name__ == "__main__":
    app = UxnApp()
    app.run()