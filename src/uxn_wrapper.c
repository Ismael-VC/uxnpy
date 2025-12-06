// uxn_wrapper.c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "uxn_wrapper.h"

/* ============================================================================
 * CORE UXN VM (UNIFIED) - Supports both CLI and GUI modes
 * ============================================================================ */

typedef struct {
    Uxn uxn;
    UxnMode mode;
    void* gui_context;  /* Points to UxnEmu when mode == UXN_MODE_GUI */
} UxnInstance;

static UxnInstance* current_instance = NULL;

Uint8 emu_dei(Uint8 addr) {
    if (!current_instance) return 0;
    return current_instance->uxn.dev[addr];
}

void emu_deo(Uint8 addr, Uint8 value) {
    if (!current_instance) return;

    current_instance->uxn.dev[addr] = value;
    switch(addr) {
    case 0x11:
        break;
    case 0x18:
        fputc(value, stdout);
        fflush(stdout);
        break;
    case 0x19:
        fputc(value, stderr);
        fflush(stderr);
        break;
    }
}

UxnHandle uxn_create(void) {
    return uxn_create_with_mode(UXN_MODE_CLI);
}

UxnHandle uxn_create_with_mode(UxnMode mode) {
    UxnInstance* instance = (UxnInstance*)malloc(sizeof(UxnInstance));
    if (!instance) return NULL;

    memset(&instance->uxn, 0, sizeof(Uxn));
    memset(instance->uxn.ram, 0, PAGE_SIZE*0x10);
    memset(instance->uxn.dev, 0, 0x100);
    memset(instance->uxn.rst.dat, 0, 0x100);
    memset(instance->uxn.wst.dat, 0, 0x100);
    instance->uxn.pc = 0x100;
    instance->uxn.wst.ptr = 0;
    instance->uxn.rst.ptr = 0;
    instance->mode = mode;
    instance->gui_context = NULL;

    static int buffering_disabled = 0;
    if (!buffering_disabled) {
        setvbuf(stdout, NULL, _IONBF, 0);
        setvbuf(stderr, NULL, _IONBF, 0);
        buffering_disabled = 1;
    }

#ifdef UXN_WITH_SDL
    if (mode == UXN_MODE_GUI) {
        instance->gui_context = uxnemu_create();
        if (!instance->gui_context) {
            free(instance);
            return NULL;
        }
    }
#endif

    return (UxnHandle)instance;
}

void uxn_destroy(UxnHandle handle) {
    if (!handle) return;

    UxnInstance* instance = (UxnInstance*)handle;

#ifdef UXN_WITH_SDL
    if (instance->mode == UXN_MODE_GUI && instance->gui_context) {
        uxnemu_destroy(instance->gui_context);
    }
#endif

    free(instance);
}

void uxn_instance_init(UxnHandle handle) {
    if (!handle) return;

    UxnInstance* instance = (UxnInstance*)handle;
    memset(&instance->uxn, 0, sizeof(Uxn));
    memset(instance->uxn.ram, 0, PAGE_SIZE*0x10);
    memset(instance->uxn.dev, 0, 0x100);
    memset(instance->uxn.rst.dat, 0, 0x100);
    memset(instance->uxn.wst.dat, 0, 0x100);
    instance->uxn.pc = 0x100;
    instance->uxn.wst.ptr = 0;
    instance->uxn.rst.ptr = 0;
}

int uxn_instance_eval(UxnHandle handle, Uint16 pc) {
    if (!handle) return 0;

    UxnInstance* instance = (UxnInstance*)handle;

#ifdef UXN_WITH_SDL
    if (instance->mode == UXN_MODE_GUI && instance->gui_context) {
        /* GUI mode - delegate to emulator */
        UxnEmu* emu = (UxnEmu*)instance->gui_context;
        current_emu = emu;
        int result = uxn_eval(&emu->uxn, pc);
        current_emu = NULL;
        return result;
    }
#endif

    /* CLI mode */
    current_instance = instance;
    int result = uxn_eval(&instance->uxn, pc);
    current_instance = NULL;

    return result;
}

int uxn_instance_load_rom(UxnHandle handle, const char* data, size_t size) {
    if (!handle || size > BANK_MAX) return -1;

    UxnInstance* instance = (UxnInstance*)handle;

#ifdef UXN_WITH_SDL
    if (instance->mode == UXN_MODE_GUI && instance->gui_context) {
        /* GUI mode - initialize GUI and create window */
        if (!uxnemu_init(instance->gui_context))
            return -1;

        /* Load ROM into GUI context */
        UxnEmu* emu = (UxnEmu*)instance->gui_context;
        memcpy(&emu->uxn.ram[PAGE_PROGRAM], data, size);

        /* Create the window */
        Uint32 window_flags = SDL_WINDOW_HIGH_PIXEL_DENSITY;
        if(emu->fullscreen)
            window_flags |= SDL_WINDOW_FULLSCREEN;

        emu->window = SDL_CreateWindow("Varvara",
            WIDTH * emu->zoom,
            HEIGHT * emu->zoom,
            window_flags);

        if(!emu->window) return -1;
        emu->window_created = 1;

        emu->renderer = SDL_CreateRenderer(emu->window, NULL);
        if(!emu->renderer) return -1;

        /* Create texture */
        SDL_SetRenderLogicalPresentation(emu->renderer, WIDTH, HEIGHT,
                                          SDL_LOGICAL_PRESENTATION_INTEGER_SCALE,
                                          SDL_SCALEMODE_NEAREST);
        emu->texture = SDL_CreateTexture(emu->renderer, SDL_PIXELFORMAT_RGBA32,
                                          SDL_TEXTUREACCESS_STATIC, WIDTH, HEIGHT);
        if(!emu->texture) return -1;

        SDL_SetTextureBlendMode(emu->texture, SDL_BLENDMODE_NONE);

        /* Initialize screen */
        screen_resize(WIDTH, HEIGHT, 1);
        emu->running = 1;

        return 0;
    }
#endif

    /* CLI mode */
    memcpy(&instance->uxn.ram[PAGE_PROGRAM], data, size);
    return 0;
}

void uxn_instance_console_input(UxnHandle handle, int c, Uint32 type) {
    if (!handle) return;

    UxnInstance* instance = (UxnInstance*)handle;
    current_instance = instance;

    instance->uxn.dev[0x12] = c;
    instance->uxn.dev[0x17] = type;

    if (!instance->uxn.dev[0x0f]) {
        uxn_eval(&instance->uxn, 0x100);
    }

    current_instance = NULL;
}

Uint8* uxn_instance_get_ram(UxnHandle handle) {
    if (!handle) return NULL;
    return ((UxnInstance*)handle)->uxn.ram;
}

Uint8* uxn_instance_get_dev(UxnHandle handle) {
    if (!handle) return NULL;
    return ((UxnInstance*)handle)->uxn.dev;
}

Uint16* uxn_instance_get_pc(UxnHandle handle) {
    if (!handle) return NULL;
    return &((UxnInstance*)handle)->uxn.pc;
}

Uint8* uxn_instance_get_wst_ptr(UxnHandle handle) {
    if (!handle) return NULL;
    return &((UxnInstance*)handle)->uxn.wst.ptr;
}

Uint8* uxn_instance_get_rst_ptr(UxnHandle handle) {
    if (!handle) return NULL;
    return &((UxnInstance*)handle)->uxn.rst.ptr;
}

Uint8* uxn_instance_get_wst(UxnHandle handle) {
    if (!handle) return NULL;
    return ((UxnInstance*)handle)->uxn.wst.dat;
}

Uint8* uxn_instance_get_rst(UxnHandle handle) {
    if (!handle) return NULL;
    return ((UxnInstance*)handle)->uxn.rst.dat;
}

void uxn_instance_set_dev(UxnHandle handle, Uint8 port, Uint8 value) {
    if (!handle) return;

    UxnInstance* instance = (UxnInstance*)handle;

#ifdef UXN_WITH_SDL
    if (instance->mode == UXN_MODE_GUI && instance->gui_context) {
        UxnEmu* emu = (UxnEmu*)instance->gui_context;
        current_emu = emu;
        emu_deo(port, value);
        current_emu = NULL;
        return;
    }
#endif

    current_instance = instance;
    emu_deo(port, value);
    current_instance = NULL;
}

UxnMode uxn_get_mode(UxnHandle handle) {
    if (!handle) return UXN_MODE_CLI;
    return ((UxnInstance*)handle)->mode;
}

int uxn_set_mode(UxnHandle handle, UxnMode mode) {
    if (!handle) return 0;
    UxnInstance* instance = (UxnInstance*)handle;

#ifdef UXN_WITH_SDL
    if (mode == UXN_MODE_GUI && instance->mode == UXN_MODE_CLI) {
        /* Switch from CLI to GUI */
        instance->gui_context = uxnemu_create();
        if (!instance->gui_context) return 0;

        /* Copy uxn state to GUI context */
        UxnEmu* emu = (UxnEmu*)instance->gui_context;
        memcpy(&emu->uxn, &instance->uxn, sizeof(Uxn));

        instance->mode = UXN_MODE_GUI;
        return 1;
    }
#endif

    if (mode == UXN_MODE_CLI && instance->mode == UXN_MODE_GUI) {
        /* Switch from GUI to CLI */
#ifdef UXN_WITH_SDL
        if (instance->gui_context) {
            UxnEmu* emu = (UxnEmu*)instance->gui_context;
            /* Copy uxn state back */
            memcpy(&instance->uxn, &emu->uxn, sizeof(Uxn));
            uxnemu_destroy(instance->gui_context);
            instance->gui_context = NULL;
        }
#endif
        instance->mode = UXN_MODE_CLI;
        return 1;
    }

    return 1; /* Already in requested mode */
}

/* ============================================================================
 * UXNEMU - GUI EMULATOR (requires SDL3)
 * ============================================================================ */

#ifdef UXN_WITH_SDL

#include <SDL3/SDL.h>
#include "devices/system.h"
#include "devices/console.h"
#include "devices/screen.h"
#include "devices/audio.h"
#include "devices/file.h"
#include "devices/controller.h"
#include "devices/mouse.h"
#include "devices/datetime.h"

#define WIDTH 64 * 8
#define HEIGHT 40 * 8

typedef struct UxnEmu {
    Uxn uxn;
    int console_vector;

    SDL_Window *window;
    SDL_Texture *texture;
    SDL_Renderer *renderer;
    SDL_Rect viewport;
    SDL_AudioStream *audio_stream;
    SDL_Thread *stdin_thread;

    int window_created;
    int fullscreen;
    int borderless;
    Uint32 zoom;

    Uint32 stdin_event;
    Uint32 audio0_event;

    int running;
} UxnEmu;

static _Thread_local UxnEmu *current_emu = NULL;

/* Audio callback */
static void
audio_callback(void *userdata, SDL_AudioStream *stream, int additional_amount, int total_amount)
{
    UxnEmu *emu = (UxnEmu *)userdata;
    int instance, running = 0;
    Sint16 samples[512 * 2];
    int len = sizeof(samples);

    (void)additional_amount;
    (void)total_amount;

    memset(samples, 0, len);
    for(instance = 0; instance < POLYPHONY; instance++)
        running += audio_render(instance, samples, samples + len / 2);

    SDL_PutAudioStreamData(stream, samples, len);

    if(!running)
        SDL_PauseAudioStreamDevice(stream);
}

void
audio_finished_handler(int instance)
{
    if(!current_emu) return;
    SDL_Event event;
    event.type = current_emu->audio0_event + instance;
    SDL_PushEvent(&event);
}

/* Device I/O for emulator */
static Uint8
audio_dei(UxnEmu *emu, int instance, Uint8 *d, Uint8 port)
{
    if(!emu->audio_stream) return d[port];
    switch(port) {
    case 0x4: return audio_get_vu(instance);
    case 0x2: POKE2(d + 0x2, audio_get_position(instance)); /* fall through */
    default: return d[port];
    }
}

static void
audio_deo(UxnEmu *emu, int instance, Uint8 *d, Uint8 port)
{
    if(!emu->audio_stream) return;
    if(port == 0xf) {
        SDL_LockAudioStream(emu->audio_stream);
        audio_start(instance, d);
        SDL_UnlockAudioStream(emu->audio_stream);
        SDL_ResumeAudioStreamDevice(emu->audio_stream);
    }
}

/* Override emu_dei/emu_deo for GUI mode */
#undef emu_dei
#undef emu_deo

Uint8
emu_dei(Uint8 addr)
{
    if(!current_emu) return 0;
    Uint8 p = addr & 0x0f, d = addr & 0xf0;
    UxnEmu *emu = current_emu;

    switch(d) {
    case 0x00: return system_dei(addr);
    case 0x20: return screen_dei(addr);
    case 0x30: return audio_dei(emu, 0, &emu->uxn.dev[d], p);
    case 0x40: return audio_dei(emu, 1, &emu->uxn.dev[d], p);
    case 0x50: return audio_dei(emu, 2, &emu->uxn.dev[d], p);
    case 0x60: return audio_dei(emu, 3, &emu->uxn.dev[d], p);
    case 0xc0: return datetime_dei(addr);
    }
    return emu->uxn.dev[addr];
}

void
emu_deo(Uint8 addr, Uint8 value)
{
    if(!current_emu) return;
    UxnEmu *emu = current_emu;
    Uint8 p = addr & 0x0f, d = addr & 0xf0;

    emu->uxn.dev[addr] = value;
    switch(d) {
    case 0x00:
        system_deo(addr);
        if(p > 0x7 && p < 0xe) screen_palette();
        break;
    case 0x10: console_deo(addr); break;
    case 0x20: screen_deo(addr); break;
    case 0x30: audio_deo(emu, 0, &emu->uxn.dev[d], p); break;
    case 0x40: audio_deo(emu, 1, &emu->uxn.dev[d], p); break;
    case 0x50: audio_deo(emu, 2, &emu->uxn.dev[d], p); break;
    case 0x60: audio_deo(emu, 3, &emu->uxn.dev[d], p); break;
    case 0x80: controller_deo(addr); break;
    case 0x90: mouse_deo(addr); break;
    case 0xa0: file_deo(addr); break;
    case 0xb0: file_deo(addr); break;
    }
}

/* Public emulator API */

UxnEmuHandle
uxnemu_create(void)
{
    UxnEmu *emu = (UxnEmu *)calloc(1, sizeof(UxnEmu));
    if(!emu) return NULL;

    emu->zoom = 1;
    emu->running = 0;

    return (UxnEmuHandle)emu;
}

void
uxnemu_destroy(UxnEmuHandle handle)
{
    if(!handle) return;
    UxnEmu *emu = (UxnEmu *)handle;

    emu->running = 0;

    if(emu->audio_stream)
        SDL_DestroyAudioStream(emu->audio_stream);
    if(emu->texture)
        SDL_DestroyTexture(emu->texture);
    if(emu->renderer)
        SDL_DestroyRenderer(emu->renderer);
    if(emu->window)
        SDL_DestroyWindow(emu->window);

    free(emu);
}

int
uxnemu_init(UxnEmuHandle handle)
{
    if(!handle) return 0;
    UxnEmu *emu = (UxnEmu *)handle;

    static int sdl_initialized = 0;
    if(!sdl_initialized) {
        if(!SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO | SDL_INIT_GAMEPAD))
            return 0;
        sdl_initialized = 1;
    }

    /* Initialize audio */
    SDL_AudioSpec spec;
    spec.freq = SAMPLE_FREQUENCY;
    spec.format = SDL_AUDIO_S16;
    spec.channels = 2;

    emu->audio_stream = SDL_OpenAudioDeviceStream(SDL_AUDIO_DEVICE_DEFAULT_PLAYBACK,
                                                    &spec, audio_callback, emu);
    if(!emu->audio_stream)
        return 0;

    emu->audio0_event = SDL_RegisterEvents(POLYPHONY);
    emu->stdin_event = SDL_RegisterEvents(1);

    return 1;
}

int
uxnemu_load_rom(UxnEmuHandle handle, const char* rom_path)
{
    if(!handle) return 0;
    UxnEmu *emu = (UxnEmu *)handle;

    current_emu = emu;

    Uint8 *ram = (Uint8 *)calloc(PAGE_SIZE * BANKS + 1, sizeof(Uint8));
    if(!ram) return 0;

    if(!system_boot(ram, rom_path, 0)) {
        free(ram);
        return 0;
    }

    memcpy(&emu->uxn, &uxn, sizeof(Uxn));
    emu->running = 1;

    return 1;
}

int
uxnemu_run(UxnEmuHandle handle)
{
    if(!handle) return 0;
    UxnEmu *emu = (UxnEmu *)handle;

    current_emu = emu;

    /* Create window and start main loop */
    char *rom_name = metadata_read_name();
    Uint32 window_flags = SDL_WINDOW_HIGH_PIXEL_DENSITY;

    if(emu->fullscreen)
        window_flags |= SDL_WINDOW_FULLSCREEN;

    emu->window = SDL_CreateWindow(rom_name,
        uxn_screen.width * emu->zoom,
        uxn_screen.height * emu->zoom,
        window_flags);

    if(!emu->window) return 0;
    emu->window_created = 1;

    emu->renderer = SDL_CreateRenderer(emu->window, NULL);
    if(!emu->renderer) return 0;

    /* Main loop handled by uxnemu_handle_events and uxnemu_redraw */
    return 1;
}

void
uxnemu_stop(UxnEmuHandle handle)
{
    if(!handle) return;
    ((UxnEmu *)handle)->running = 0;
}

void
uxnemu_set_zoom(UxnEmuHandle handle, int zoom)
{
    if(!handle || zoom < 1) return;
    UxnEmu *emu = (UxnEmu *)handle;
    emu->zoom = zoom;
}

void
uxnemu_set_fullscreen(UxnEmuHandle handle, int fullscreen)
{
    if(!handle) return;
    UxnEmu *emu = (UxnEmu *)handle;
    emu->fullscreen = fullscreen;
    if(emu->window)
        SDL_SetWindowFullscreen(emu->window, fullscreen ? SDL_TRUE : SDL_FALSE);
}

void
uxnemu_set_borderless(UxnEmuHandle handle, int borderless)
{
    if(!handle) return;
    UxnEmu *emu = (UxnEmu *)handle;
    if(emu->fullscreen) return;
    emu->borderless = borderless;
    if(emu->window)
        SDL_SetWindowBordered(emu->window, !borderless);
}

Uint8*
uxnemu_get_ram(UxnEmuHandle handle)
{
    if(!handle) return NULL;
    return ((UxnEmu *)handle)->uxn.ram;
}

Uint8*
uxnemu_get_dev(UxnEmuHandle handle)
{
    if(!handle) return NULL;
    return ((UxnEmu *)handle)->uxn.dev;
}

Uint16
uxnemu_get_pc(UxnEmuHandle handle)
{
    if(!handle) return 0;
    return ((UxnEmu *)handle)->uxn.pc;
}

Uint8*
uxnemu_get_wst_ptr(UxnEmuHandle handle)
{
    if(!handle) return NULL;
    return &((UxnEmu *)handle)->uxn.wst.ptr;
}

Uint8*
uxnemu_get_rst_ptr(UxnEmuHandle handle)
{
    if(!handle) return NULL;
    return &((UxnEmu *)handle)->uxn.rst.ptr;
}

Uint8*
uxnemu_get_wst(UxnEmuHandle handle)
{
    if(!handle) return NULL;
    return ((UxnEmu *)handle)->uxn.wst.dat;
}

Uint8*
uxnemu_get_rst(UxnEmuHandle handle)
{
    if(!handle) return NULL;
    return ((UxnEmu *)handle)->uxn.rst.dat;
}

int
uxnemu_is_running(UxnEmuHandle handle)
{
    if(!handle) return 0;
    return ((UxnEmu *)handle)->running;
}

int
uxnemu_handle_events(UxnEmuHandle handle)
{
    if(!handle) return 0;
    UxnEmu *emu = (UxnEmu *)handle;
    current_emu = emu;

    SDL_Event event;
    while(SDL_PollEvent(&event)) {
        if(event.type == SDL_EVENT_QUIT) {
            emu->running = 0;
            return 0;
        }
        else if(event.type == SDL_EVENT_WINDOW_EXPOSED)
            uxnemu_redraw(handle);
        else if(event.type == SDL_EVENT_MOUSE_MOTION)
            mouse_pos(event.motion.x, event.motion.y);
        else if(event.type == SDL_EVENT_MOUSE_BUTTON_UP)
            mouse_up(event.button.button);
        else if(event.type == SDL_EVENT_MOUSE_BUTTON_DOWN)
            mouse_down(event.button.button);
        else if(event.type == SDL_EVENT_MOUSE_WHEEL)
            mouse_scroll(event.wheel.x, event.wheel.y);
        else if(event.type == SDL_EVENT_KEY_DOWN) {
            if(event.key.key == SDLK_ESCAPE) {
                emu->running = 0;
                return 0;
            }
            else if(event.key.key == SDLK_F11) {
                emu->fullscreen = !emu->fullscreen;
                SDL_SetWindowFullscreen(emu->window, emu->fullscreen ? SDL_TRUE : SDL_FALSE);
            }
        }
    }

    return 1;
}

void
uxnemu_redraw(UxnEmuHandle handle)
{
    if(!handle) return;
    UxnEmu *emu = (UxnEmu *)handle;

    if(!emu->texture || !emu->renderer || !emu->window_created) return;

    SDL_UpdateTexture(emu->texture, NULL, uxn_screen.pixels,
                      uxn_screen.width * sizeof(Uint32));
    SDL_SetRenderDrawColor(emu->renderer, 0, 0, 0, 255);
    SDL_RenderClear(emu->renderer);
    SDL_RenderTexture(emu->renderer, emu->texture, NULL, NULL);
    SDL_RenderPresent(emu->renderer);
}

#endif /* UXN_WITH_SDL */
