# src/asm.py
def assemble(uxntal: str) -> bytearray:
    """Simple Uxntal assembler."""
    rom = bytearray()
    for line in uxntal.splitlines():
        line = line.strip()
        if line.startswith('|0100'):
            continue  # Start address
        tokens = line.split()
        if not tokens:
            continue
        if tokens[0].startswith('#'):
            val = int(tokens[0][1:], 16)
            rom.append(0xa0 if val > 0xff else 0x80)
            rom.append(val & 0xff)
            if val > 0xff:
                rom.append((val >> 8) & 0xff)
        elif tokens[0] == '.Console/write':
            rom.append(0x18)
        elif tokens[0] == 'DEO':
            rom.append(0x17)
    return rom