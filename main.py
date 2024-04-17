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

def segments(coords, flags):
    i = 0
    all_segments = []
    while i < len(flags):
        segment = []
        while i < len(flags):
            on_curve = flags[i] & 1
            if on_curve and segment == []:
                segment.append(coords[i])
            elif not on_curve:
                segment.append(coords[i])
            elif on_curve and segment != []:
                segment.append(coords[i])

                # if there are more than 4 total points
                # it indicates that we have at least 2 control points
                # eg: [p1, c1, c2, p2]
                # since true-type fonts use quadratic bezier curves
                # the encoding basically skips the middle anchor point
                # but it can be calculated as the midpoint between 2 control points
                # 
                # reference: https://stackoverflow.com/a/20772557/9985287
                if len(segment) >= 4:
                    # add the first two points
                    enhanced_segment = [segment[0], segment[1]]

                    for x in range(1, len(segment)-1):
                        c1, c2 = segment[x], segment[x+1]
                        pnx = (c1[0] + c2[0]) // 2
                        pny = (c1[1] + c2[1]) // 2
                        pn = (pnx, pny)
                        # add the midpoint and the next point
                        enhanced_segment.append(pn)
                        enhanced_segment.append(c2)
                    # add the last point to the segment
                    enhanced_segment.append(segment[-1])
                else:
                    enhanced_segment = segment
                all_segments.append(enhanced_segment)
                # i is moved back because the last on-curve point we explored
                # is actually a start point of the next curve
                # TODO: this probably is causing issues for the inner detached section
                # TODO: look at the winding contour data
                i -= 1
                break
            i += 1
        i += 1
    return all_segments

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

        main_coords = list(glyph['coordinates'])
        main_flags = list(glyph['flags'])

        all_segments = segments(main_coords+[main_coords[0]], main_flags + [main_flags[0]])
        
        rl.begin_drawing()
        rl.clear_background(rl.BLACK)

        scaling_factor = 2
        font_width, font_height = find_char_width_height(main_coords)

        translate_x = rl.get_screen_width() // 2 - font_width // (scaling_factor * 2)
        translate_y = rl.get_screen_height() // 2 + font_height // (scaling_factor * 2)

        def transform(pair):
            p1x, p1y = pair
            x, y = translate_x + p1x//scaling_factor, translate_y-p1y//scaling_factor
            return rl.Vector2(x, y)

        for segment in all_segments:
            if len(segment) == 2:
                pts = list(map(transform, segment))
                s, e = pts
                rl.draw_line_v(
                    s, e, rl.WHITE
                )
            else:
                pts = list(map(transform, segment))
                point_count = len(pts)
                rl.draw_spline_bezier_quadratic(
                    pts, point_count, 1.5, rl.WHITE
                )
            
        rl.end_drawing()
    rl.close_window()