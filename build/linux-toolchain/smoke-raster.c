#include <stdio.h>
#include <stdint.h>
#include "include/c/sk_general.h"
#include "include/c/sk_surface.h"
#include "include/c/sk_canvas.h"
#include "hb.h"
#ifndef STATICLINK_EXPECTED_MILESTONE
#error "Pass the milestone detected from this source tree"
#endif
int main(void) {
    if (sk_version_get_milestone() != STATICLINK_EXPECTED_MILESTONE) return 1;
    sk_imageinfo_t info = {NULL, 8, 8, RGBA_8888_SK_COLORTYPE, PREMUL_SK_ALPHATYPE};
    sk_surface_t *surface = sk_surface_new_raster(&info, 0, NULL);
    if (!surface) return 2;
    sk_canvas_clear(sk_surface_get_canvas(surface), 0xff336699u);
    uint8_t pixels[8*8*4];
    if (!sk_surface_read_pixels(surface, &info, pixels, 8*4, 0, 0)) return 3;
    for (int i=0; i<8*8; i++) {
        if (pixels[i*4] != 0x33 || pixels[i*4+1] != 0x66 || pixels[i*4+2] != 0x99 || pixels[i*4+3] != 0xff) return 4;
    }
    sk_surface_unref(surface);
    hb_buffer_t *buffer = hb_buffer_create();
    hb_buffer_add_utf8(buffer, "A\xe4\xb8\xad", 4, 0, -1);
    hb_buffer_guess_segment_properties(buffer);
    unsigned length = 0;
    hb_glyph_info_t *glyphs = hb_buffer_get_glyph_infos(buffer, &length);
    if (length != 2 || glyphs[0].codepoint != 65 || glyphs[1].codepoint != 0x4e2d) return 5;
    hb_buffer_destroy(buffer);
    printf("PASS Skia=%s HarfBuzz=%s raster=64 pixels UTF8=2 codepoints\n", sk_version_get_string(), hb_version_string());
    return 0;
}
