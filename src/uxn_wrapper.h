// uxn_wrapper.h
#ifndef UXN_WRAPPER_H
#define UXN_WRAPPER_H

#include <stddef.h>
#include "uxn/uxn.h"

#define BANK_MAX 0xfff00

typedef void* UxnHandle;

/* Uxn mode selection */
typedef enum {
    UXN_MODE_CLI = 0,  /* Headless/console mode (default) */
    UXN_MODE_GUI = 1   /* GUI mode with SDL */
} UxnMode;

/* Core Uxn VM (unified interface) */
UxnHandle uxn_create(void);
UxnHandle uxn_create_with_mode(UxnMode mode);
void uxn_destroy(UxnHandle handle);
void uxn_instance_init(UxnHandle handle);
int uxn_instance_eval(UxnHandle handle, Uint16 pc);
int uxn_instance_load_rom(UxnHandle handle, const char* data, size_t size);
void uxn_instance_console_input(UxnHandle handle, int c, Uint32 type);

/* Mode control */
UxnMode uxn_get_mode(UxnHandle handle);
int uxn_set_mode(UxnHandle handle, UxnMode mode);

/* Core Uxn state access */
Uint16* uxn_instance_get_pc(UxnHandle handle);
Uint8* uxn_instance_get_ram(UxnHandle handle);
Uint8* uxn_instance_get_dev(UxnHandle handle);
Uint8* uxn_instance_get_wst_ptr(UxnHandle handle);
Uint8* uxn_instance_get_rst_ptr(UxnHandle handle);
Uint8* uxn_instance_get_wst(UxnHandle handle);
Uint8* uxn_instance_get_rst(UxnHandle handle);
void uxn_instance_set_dev(UxnHandle handle, Uint8 port, Uint8 value);

/* Uxn Emulator with GUI (requires SDL3) */
typedef void* UxnEmuHandle;

/* Emulator lifecycle */
UxnEmuHandle uxnemu_create(void);
void uxnemu_destroy(UxnEmuHandle handle);
int uxnemu_init(UxnEmuHandle handle);
int uxnemu_load_rom(UxnEmuHandle handle, const char* rom_path);
int uxnemu_run(UxnEmuHandle handle);
void uxnemu_stop(UxnEmuHandle handle);

/* Emulator configuration */
void uxnemu_set_zoom(UxnEmuHandle handle, int zoom);
void uxnemu_set_fullscreen(UxnEmuHandle handle, int fullscreen);
void uxnemu_set_borderless(UxnEmuHandle handle, int borderless);

/* Emulator state access */
Uint8* uxnemu_get_ram(UxnEmuHandle handle);
Uint8* uxnemu_get_dev(UxnEmuHandle handle);
Uint16 uxnemu_get_pc(UxnEmuHandle handle);
Uint8* uxnemu_get_wst_ptr(UxnEmuHandle handle);
Uint8* uxnemu_get_rst_ptr(UxnEmuHandle handle);
Uint8* uxnemu_get_wst(UxnEmuHandle handle);
Uint8* uxnemu_get_rst(UxnEmuHandle handle);
int uxnemu_is_running(UxnEmuHandle handle);

/* Emulator event handling */
int uxnemu_handle_events(UxnEmuHandle handle);
void uxnemu_redraw(UxnEmuHandle handle);

#endif // UXN_WRAPPER_H
