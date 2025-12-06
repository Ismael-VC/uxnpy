/*
Copyright (u) 2022-2025 Devine Lu Linvega, Andrew Alderwick,
                        Ismael Venegas Castelló

Permission to use, copy, modify, and distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE.
*/

#define PAGE_SIZE 0x100000
#define PAGE_PROGRAM 0x0100
#define STEP_MAX 0x10000

typedef unsigned char Uint8;
typedef signed char Sint8;
typedef unsigned short Uint16;
typedef signed short Sint16;
typedef unsigned int Uint32;

typedef struct {
    Uint8 dat[0x100], ptr;
} Stack;

typedef struct Uxn {
    Uint8 ram[PAGE_SIZE*0x10], dev[0x100];
    Stack wst, rst;
    Uint16 pc;
} Uxn;

int uxn_eval(Uxn *u, Uint16 pc);

Uint8 emu_dei(Uint8 addr);
void emu_deo(Uint8 addr, Uint8 value);
