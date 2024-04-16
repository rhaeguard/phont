from fontTools.ttLib import TTFont
import pyray as rl

# Open the TTF file
font = TTFont('./assets/EBGaramond/EBGaramond-Regular.ttf')

# Access the glyf table
glyf_table = font['glyf']

# close the font file
font.close()

def find_char_width_height(coords) -> tuple[int, int]:
    x_min, x_max = coords[0][0], coords[0][0]
    y_min, y_max = coords[0][1], coords[0][1]
    for x, y in coords:
        x_min = min(x_min, x)
        x_max= max(x_max, x)

        y_min = min(y_min, y)
        y_max= max(y_max, y)

    return (x_max - x_min), (y_max - y_min)

if __name__ == "__main__":
    rl.init_window(0, 0, "font-rendering")
    rl.set_target_fps(15)
    rl.toggle_fullscreen()
    
    prev_keycode = 65 # capital letter A

    while not rl.window_should_close():
        keycode = rl.get_key_pressed()
        keycode = keycode if keycode != 0 else prev_keycode
        key = chr(keycode)
        prev_keycode = keycode

        glyph = glyf_table[key].__dict__
        
        main_coords = glyph['coordinates']
        # create pair of coordinates to draw lines between
        pairs = zip(main_coords, main_coords[1:] + [main_coords[0]])

        rl.begin_drawing()
        rl.clear_background(rl.BLACK)

        scaling_factor = 2
        font_width, font_height = find_char_width_height(main_coords)

        translate_x = rl.get_screen_width() // 2 - font_width // (scaling_factor * 2)
        translate_y = rl.get_screen_height() // 2 + font_height // (scaling_factor * 2)

        # this is a very simple rendering technique
        # just draws a straight line from one point to another
        for p1, p2 in pairs:

            p1x, p1y = p1
            p2x, p2y = p2

            rl.draw_line(
                translate_x + p1x//scaling_factor, translate_y-p1y//scaling_factor,
                translate_x + p2x//scaling_factor, translate_y-p2y//scaling_factor,
                rl.WHITE
            )


        rl.end_drawing()
    rl.close_window()