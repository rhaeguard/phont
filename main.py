from typing import Any
from fontTools.ttLib import TTFont
import pyray as rl
import random as rand

# Open the TTF file
font = TTFont('./assets/EBGaramond/EBGaramond-Regular.ttf')

# Access the glyf table
glyf_table = font['glyf']

# close the font file
font.close()

def find_char_width_height(glyph) -> tuple[int, int]:
    coords = list(glyph['coordinates'])

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

                # if there are more than 3 total points
                # it indicates that we have at least 2 control points
                # eg: [p1, c1, c2, p2]
                # since true-type fonts use quadratic bezier curves
                # the encoding basically skips the middle anchor point
                # but it can be calculated as the midpoint between 2 control points
                # 
                # reference: https://stackoverflow.com/a/20772557/9985287
                if len(segment) > 3:
                    # add the first two points
                    enhanced_segment = [segment[0], segment[1]]

                    for x in range(1, len(segment)-2):
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
                i -= 1
                break
            i += 1
        i += 1
    return all_segments

def all_contour_segments(glyph: dict[str, Any]):
    coords = list(glyph['coordinates'])
    flags = list(glyph['flags'])
    end_of_contours = list(glyph['endPtsOfContours'])

    all_contours = []
    start = 0
    for end in end_of_contours:
        # start, end
        segment_coords = coords[start:end+1]
        segment_coords = segment_coords + [segment_coords[0]] # include the first entry to close the loop

        segment_flags = flags[start:end+1]
        segment_flags = segment_flags + [segment_flags[0]] # include the first entry to close the loop
        
        all_segments_in_contour = segments(segment_coords, segment_flags)
        all_contours.extend(all_segments_in_contour)
        start = end+1
    return all_contours

if __name__ == "__main__":
    rl.init_window(0, 0, "font-rendering")
    rl.set_target_fps(15)
    rl.toggle_fullscreen()
    
    prev_keycode = 65 # capital letter A

    while not rl.window_should_close():
        keycode = rl.get_key_pressed()
        keycode = keycode if keycode in range(65, 65+29) else prev_keycode
        key = chr(keycode)
        prev_keycode = keycode

        glyph = glyf_table[key].__dict__

        all_segments = all_contour_segments(glyph)
        
        rl.begin_drawing()
        rl.clear_background(rl.BLACK)

        scaling_factor = 2
        font_width, font_height = find_char_width_height(glyph)

        translate_x = rl.get_screen_width() // 2 - font_width // (scaling_factor * 2)
        translate_y = rl.get_screen_height() // 2 + font_height // (scaling_factor * 2)

        def transform(pair):
            p1x, p1y = pair
            x, y = translate_x + p1x//scaling_factor, translate_y-p1y//scaling_factor
            return rl.Vector2(x, y)

        for segment in all_segments:
            if len(segment) == 2:
                pts = list(map(transform, segment))
                segment, e = pts
                rl.draw_line_v(
                    segment, e, rl.WHITE
                )
            else:
                pts = list(map(transform, segment))
                point_count = len(pts)
                for x in range(0, point_count-1, 2):
                    pt = pts[x:x+3]
                    rl.draw_spline_bezier_quadratic(
                        pt, 3, 1, rl.WHITE
                    )

        rl.end_drawing()
        
    rl.close_window()