import logging
from textual.app import App, ComposeResult
from textual.widgets import RichLog, Input, Static, Footer
from textual.worker import Worker
from .emu import Emu
from .devices.console import Console
import sys
from typing import Optional

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

def poke16(mem: bytearray, addr: int, val: int) -> None:
    """Helper to write 16-bit value."""
    mem[addr] = (val >> 8) & 0xff
    mem[addr + 1] = val & 0xff

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

    async def process_assembler(self, uxntal_code: str) -> tuple[bytearray, str]:
        """Async function to process assembler evaluation."""
        logger.debug(f"Processing assembler input: {uxntal_code}")
        # Clear assembler's buffers
        self.assembler.console.output_buffer = bytearray()
        self.assembler.console.error_buffer = bytearray()
        # Send Uxntal code to assembler
        self.assembler.console.on_console(uxntal_code)
        # Set input vector
        poke16(self.assembler.uxn.dev, 0x10, 0x0100)
        # Run eval with a step limit to avoid blocking
        max_steps = 10000
        steps = 0
        logger.debug(f"Starting eval at 0x0100 with max {max_steps} steps")
        while self.assembler.uxn.pc != 0 and steps < max_steps:
            self.assembler.uxn.step()
            steps += 1
        logger.debug(f"Eval completed after {steps} steps, PC: {self.assembler.uxn.pc:04x}")
        # Get results
        status_message = self.assembler.console.error_buffer.decode('ascii', errors='ignore')
        assembled_rom = self.assembler.console.output_buffer
        logger.debug(f"Assembler output - ROM: {assembled_rom.hex()}, Status: {status_message}")
        return assembled_rom, status_message

    def on_input_submitted(self, event: Input.Submitted) -> None:
        logger.debug(f"Input submitted: {event.value}")
        uxntal_code = event.value
        # Start assembler processing in a background task
        self.process_worker = self.create_task(self.process_assembler(uxntal_code))
        self.process_worker.add_done_callback(lambda task: self._on_assembler_done(task.result()))

    def _on_assembler_done(self, result: tuple[bytearray, str]) -> None:
        """Handle the result of the assembler task."""
        assembled_rom, status_message = result
        logger.debug(f"Assembler task done - ROM: {assembled_rom.hex()}, Status: {status_message}")
        # Update UI
        self.query_one(RichLog).write(f"Input Uxntal:\n{uxntal_code}\n")
        self.query_one(RichLog).write(f"Assembler: {status_message}\n")
        self.query_one(RichLog).write(f"Assembled ROM: {assembled_rom.hex()}\n")
        # Load assembled ROM into primary emulator
        if assembled_rom:
            logger.info(f"Loading assembled ROM into primary Emu: {assembled_rom.hex()}")
            self.emu.load(assembled_rom)
        else:
            logger.warning("No assembled ROM produced")
        # Refocus input
        self.query_one(Input).focus()
        logger.debug("Input widget refocused")
        self.update_repr()

    def on_key(self, event) -> None:
        logger.debug(f"Key event: {event.key} (pressed: {event.is_pressed})")
        if event.key == "escape":
            self.app.exit()

if __name__ == "__main__":
    app = UxnApp()
    app.run()