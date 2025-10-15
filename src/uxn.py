from typing import Any, Optional
import logging


logger = logging.getLogger(__name__)

class Stack:
    def __init__(self, u: 'Uxn', name: str) -> None:
        self.ram: bytearray = bytearray(0x100)
        self.ptr: int = 0
        self.ptrk: int = 0
        self.name: str = name

    def PU1(self, val: int) -> None: 
        self.ram[self.ptr & 0xff] = val & 0xff
        self.ptr += 1
    
    def PU2(self, val: int) -> None: 
        self.PU1(val >> 8)
        self.PU1(val)
    
    def PO1(self) -> int: 
        self.ptr -= 1
        return self.ram[self.ptr & 0xff]
    
    def PO2(self) -> int: 
        return self.PO1() | (self.PO1() << 8)

    def __repr__(self) -> str:
        res = f"{self.name} "
        i = self.ptr - 8
        while i != self.ptr:
            res += f"{self.ram[i & 0xff]:02x}"
            res += " " if ((i + 1) & 0xff) else "|"
            i += 1
        res += f"<{self.ptr:02x}"
        return res


class Uxn:
    def __init__(self, emu: Optional[Any] = None) -> None:
        self.emu: Optional[Any] = emu
        self.dev: bytearray = bytearray(0x100)
        self.wst: Stack = Stack(self, "WST")
        self.rst: Stack = Stack(self, "RST")
        self.ram: bytearray = bytearray(0x10000)
        self.pc: int = 0
        self.m2: bool = False
        self.mk: bool = False
        self.src: Stack = self.wst
        self.dst: Stack = self.rst
        self.x: list[int] = [0, 0]
        self.y: list[int] = [0, 0]
        self.z: list[int] = [0, 0]

    def JMP(self, i: int) -> None:
        self.pc = i &0xffff if self.m2 else (self.pc + self.sig(i)) & 0xffff

    def JMI(self) -> None:
        a = (self.ram[self.pc] << 8) | self.ram[self.pc + 1]
        self.pc += 2
        self.pc = (self.pc + a) & 0xffff

    def POx(self) -> int:
        return self.src.PO2() if self.m2 else self.src.PO1()

    def PUx(self, x: int) -> None:
        self.src.PU2(x) if self.m2 else self.src.PU1(x)

    def GET(self, o: list[int]) -> None:
        o[0] = self.src.PO1()
        if self.m2: 
            o[1] = self.src.PO1()

    def PUT(self, i: list[int]) -> None:
        self.src.PU1(i[0])
        if self.m2: 
            self.src.PU1(i[1])

    def DEI(self, i: int, o: list[int]) -> None:
        o[0] = self.emu.dei(i) if self.emu else 0
        if self.m2:
            o[1] = self.emu.dei((i + 1) & 0xff) if self.emu else 0
        self.PUT(o)

    def DEO(self, i: int, j: list[int]) -> None:
        if self.emu:
            self.emu.deo(i, j[0])
            if self.m2:
                self.emu.deo((i + 1) & 0xff, j[1])

    def PEK(self, i: int, o: list[int], m: int) -> None:
        o[0] = self.ram[i & 0xffff]
        if self.m2:
            o[1] = self.ram[(i + 1) & m]
        self.PUT(o)

    def POK(self, i: int, j: list[int], m: int) -> None:
        self.ram[i & 0xffff] = j[0]
        if self.m2:
            self.ram[(i + 1) & m] = j[1]

    def k(self) -> None:
        if self.mk: 
            self.src.ptr = self.src.ptrk

    def step(self) -> int:
        ins = self.ram[self.pc]
        self.pc = (self.pc + 1) & 0xffff
        self.m2 = bool(ins & 0x20)
        if ins & 0x40:
            self.src = self.rst
            self.dst = self.wst
        else:
            self.src = self.wst
            self.dst = self.rst
        self.mk = bool(ins & 0x80)
        if self.mk:
            self.src.ptrk = self.src.ptr
        op = ins & 0x1f
        if op == 0x00:
            if ins == 0x00:    # BRK
                return 0
            elif ins == 0x20:  # JCI
                if self.src.PO1():
                    self.JMI()
                else:
                    self.pc = (self.pc + 2) & 0xffff
            elif ins == 0x40:  # JMI
                self.JMI()
            elif ins == 0x60:  # JSI
                self.dst.PU2(self.pc + 2)
                self.JMI()
            elif ins == 0x80:  # LIT
                self.src.PU1(self.ram[self.pc])
                self.pc = (self.pc + 1) & 0xffff
            elif ins == 0xa0:  # LI2
                self.src.PU1(self.ram[self.pc])
                self.pc = (self.pc + 1) & 0xffff
                self.src.PU1(self.ram[self.pc])
                self.pc = (self.pc + 1) & 0xffff
            elif ins == 0xc0:  # L2r
                self.dst.PU1(self.ram[self.pc])
                self.pc = (self.pc + 1) & 0xffff
            elif ins == 0xe0:  # LIr
                self.dst.PU1(self.ram[self.pc])
                self.pc = (self.pc + 1) & 0xffff
                self.dst.PU1(self.ram[self.pc])
                self.pc = (self.pc + 1) & 0xffff
        elif op == 0x01:  # INC
            a = self.POx()
            self.k()
            self.PUx((a + 1) & 0xffff)
        elif op == 0x02:  # POP
            self.POx()
            self.k()
        elif op == 0x03:  # NIP
            self.GET(self.x)
            self.POx()
            self.k()
            self.PUT(self.x)
        elif op == 0x04:  # SWP
            self.GET(self.x)
            self.GET(self.y)
            self.k()
            self.PUT(self.x)
            self.PUT(self.y)
        elif op == 0x05:  # ROT
            self.GET(self.x)
            self.GET(self.y)
            self.GET(self.z)
            self.k()
            self.PUT(self.y)
            self.PUT(self.x)
            self.PUT(self.z)
        elif op == 0x06:  # DUP
            self.GET(self.x)
            self.k()
            self.PUT(self.x)
            self.PUT(self.x)
        elif op == 0x07:  # OVR
            self.GET(self.x)
            self.GET(self.y)
            self.k()
            self.PUT(self.y)
            self.PUT(self.x)
            self.PUT(self.y)
        elif op == 0x08:  # EQU
            a = self.POx()
            b = self.POx()
            self.k()
            self.src.PU1(1 if b == a else 0)
        elif op == 0x09:  # NEQ
            a = self.POx()
            b = self.POx()
            self.k()
            self.src.PU1(1 if b != a else 0)
        elif op == 0x0a:  # GTH
            a = self.POx()
            b = self.POx()
            self.k()
            self.src.PU1(1 if b > a else 0)
        elif op == 0x0b:  # LTH
            a = self.POx()
            b = self.POx()
            self.k()
            self.src.PU1(1 if b < a else 0)
        elif op == 0x0c:  # JMP
            a = self.POx()
            self.k()
            self.JMP(a)
        elif op == 0x0d:  # JCN
            a = self.POx()
            b = self.src.PO1()
            self.k()
            if b:
                self.JMP(a)
        elif op == 0x0e:  # JSR
            a = self.POx()
            self.k()
            self.dst.PU2(self.pc)
            self.JMP(a)
        elif op == 0x0f:  # STH
            self.GET(self.x)
            self.k()
            self.dst.PU1(self.x[0])
            if self.m2:
                self.dst.PU1(self.x[1])
        elif op == 0x10:  # LDZ
            a = self.src.PO1()
            self.k()
            self.PEK(a, self.x, 0xff)
        elif op == 0x11:  # STZ
            a = self.src.PO1()
            self.GET(self.y)
            self.k()
            self.POK(a, self.y, 0xff)
        elif op == 0x12:  # LDR
            a = self.src.PO1()
            self.k()
            addr = (self.pc + self.sig(a)) & 0xffff
            self.PEK(addr, self.x, 0xffff)
        elif op == 0x13:  # STR
            a = self.src.PO1()
            self.GET(self.y)
            self.k()
            addr = (self.pc + self.sig(a)) & 0xffff
            self.POK(addr, self.y, 0xffff)
        elif op == 0x14:  # LDA
            a = self.src.PO2()
            self.k()
            self.PEK(a, self.x, 0xffff)
        elif op == 0x15:  # STA
            a = self.src.PO2()
            self.GET(self.y)
            self.k()
            self.POK(a, self.y, 0xffff)
        elif op == 0x16:  # DEI
            a = self.src.PO1()
            self.k()
            self.DEI(a, self.x)
        elif op == 0x17:  # DEO
            a = self.src.PO1()
            self.GET(self.y)
            self.k()
            self.DEO(a, self.y)
        elif op == 0x18:  # ADD
            a = self.POx()
            b = self.POx()
            self.k()
            self.PUx((b + a) & 0xffff)
        elif op == 0x19:  # SUB
            a = self.POx()
            b = self.POx()
            self.k()
            self.PUx((b - a) & 0xffff)
        elif op == 0x1a:  # MUL
            a = self.POx()
            b = self.POx()
            self.k()
            self.PUx((b * a) & 0xffff)
        elif op == 0x1b:  # DIV
            a = self.POx()
            b = self.POx()
            self.k()
            self.PUx((b // a) & 0xffff if a else 0)
        elif op == 0x1c:  # AND
            a = self.POx()
            b = self.POx()
            self.k()
            self.PUx(b & a)
        elif op == 0x1d:  # ORA
            a = self.POx()
            b = self.POx()
            self.k()
            self.PUx(b | a)
        elif op == 0x1e:  # EOR
            a = self.POx()
            b = self.POx()
            self.k()
            self.PUx(b ^ a)
        elif op == 0x1f:  # SFT
            a = self.src.PO1()
            b = self.POx()
            self.k()
            shift_right = a & 0xf
            shift_left = (a >> 4) & 0xf
            self.PUx(((b >> shift_right) << shift_left) & 0xffff)
        return ins

    def load(self, program: list[int]) -> 'Uxn':
        for i, b in enumerate(program): 
            self.ram[0x100 + i] = b
        return self

    def run(self, program: list[int]) -> 'Uxn': 
        return self.load(program).eval()

    def eval(self, at: int = 0x100) -> 'Uxn':
        logger.debug(f"Eval starting at addr: {at:04x}, PC: {self.pc:04x}")
        self.pc = at
        steps = 0x80000
        while steps > 0 and self.step():
            if self.emu and hasattr(self.emu, 'update_repr'):
                self.emu.update_repr()
            steps -= 1
        return self

    def sig(self, val: int) -> int: 
        return val - 256 if val >= 0x80 else val

    def __repr__(self) -> str: 
        return f"{self.wst}\n{self.rst}"
