from typing import Any
from fontTools.ttLib import TTFont
import pyray as rl
from glfw_constants import *
from utils import *

# Open the TTF file
font = TTFont('./assets/EBGaramond/EBGaramond-Regular.ttf')

# Access the glyph table
glyf_table = font['glyf']
# hmtx contains the advance width for characters that have no contour like space
hmtx = font['hmtx']

# close the font file
font.close()

class ProgramState:
    draw_bounding_box = False
    draw_base_line = False
    draw_curve_points = True
    scaling_factor = 4
    outline_segments: list[list[GlyphContour]] = []
    glyph_boundaries: list[rl.Rectangle] = []
    base_y: int = -1
    user_inputs: list[str] = ['t']
    text_centered: bool = False
    shift_pressed: bool = False
    caps_lock_on: bool = False

STATE = ProgramState()

def find_char_width_height(glyph) -> tuple[int, int, list[int, int, int, int]]:
    """
    required for translation
    """
    x_min, x_max = glyph["xMin"], glyph["xMax"]
    y_min, y_max = glyph["yMin"], glyph["yMax"]
    return (x_max - x_min), (y_max - y_min), [x_min, y_min, x_max, y_max]

def segments(coords, flags) -> list[list[tuple[int, int]]]:
    """
    given a set of points (coordinates) and flags indicating if they are on-curve or off-curve,
    return the segments that form the glyph

    this segment can either be a line or a quadratic bezier curve
    lines have 2 points - start and end (both on-curve)
    quadratic bezier curves have 3 points - 2 anchors (start and end, on-curve) and 1 control point (which is off-curve)
    """
    i = 0
    all_segments = []
    # there's a flag per coordinate
    # the least significant bit in the flag indicates if the point is on-curve or off-curve
    while i < len(flags):
        segment = []
        while i < len(flags):
            on_curve = flags[i] & 1
            if on_curve and segment == []:
                # if this is an anchor indicating start
                segment.append(coords[i])
            elif not on_curve:
                # if this is a control point
                segment.append(coords[i])
            elif on_curve and segment != []:
                # if this is an anchor indicating end
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
                    expanded_segment = [segment[0], segment[1]]

                    for x in range(1, len(segment)-2):
                        c1, c2 = segment[x], segment[x+1]
                        # find the midpoint between two control points
                        pnx = (c1[0] + c2[0]) // 2
                        pny = (c1[1] + c2[1]) // 2
                        pn = (pnx, pny)
                        # add the midpoint and the next point
                        expanded_segment.append(pn)
                        expanded_segment.append(c2)
                    # add the last point to the segment
                    expanded_segment.append(segment[-1])

                    # at this point expanded_segment has all the points/coordinates
                    # we now need to extract quadratic bezier curves out of these
                    point_count = len(expanded_segment)
                    # basically it's a sliding window of size 3
                    # elements are arranged as: p1 c2 p3 c4 p5 c6...
                    # so we just have a window that'll capture
                    #       p1 c2 p3
                    #       p3 c4 p5
                    #       etc.
                    for x in range(0, point_count-1, 2):
                        pts = expanded_segment[x:x+3]
                        all_segments.append(pts)
                else:
                    all_segments.append(segment)
                i -= 1 # go back because the end dot is actually shared between curves
                break
            i += 1
        i += 1
    return all_segments

def handle_compound_glyphs(glyph: dict[str, Any]) -> list[GlyphContour]:
    all_components = glyph['components']

    result:list[GlyphContour] = []
    for component in all_components:
        glyph_name, transformation = component.getComponentInfo()
        g = glyf_table[glyph_name].__dict__
        result.extend(all_contour_segments(g))
    
    return result

def all_contour_segments(glyph: dict[str, Any]) -> list[GlyphContour]:
    coords = list(glyph['coordinates'])
    flags = list(glyph['flags'])
    # endPtsOfContours contains indices that indicate the end of a contour
    # these are useful to extract out however many contours a particular glyph has
    end_of_contours = list(glyph['endPtsOfContours'])

    all_contours: list[GlyphContour] = []
    start = 0
    for end in end_of_contours:
        segment_coords = coords[start:end+1]
        segment_coords = segment_coords + [segment_coords[0]] # include the first entry to close the loop

        segment_flags = flags[start:end+1]
        segment_flags = segment_flags + [segment_flags[0]] # include the first entry to close the loop
        
        all_segments_in_contour = segments(segment_coords, segment_flags)
        contour = GlyphContour(
            segments=all_segments_in_contour
        )
        all_contours.append(contour)
        start = end+1
    return all_contours


def grab_user_input():
    keycode = rl.get_key_pressed()
    if keycode:
        if keycode == GLFW_KEY_BACKSPACE:
            # it's backspace
            if len(STATE.user_inputs) > 0:
                STATE.user_inputs.pop()
        elif keycode == GLFW_KEY_CAPS_LOCK:
            STATE.caps_lock_on = not STATE.caps_lock_on
        elif keycode == GLFW_KEY_ENTER:
            STATE.user_inputs.append("phont_newline")
        else:
            STATE.shift_pressed = rl.is_key_down(GLFW_KEY_LEFT_SHIFT) or rl.is_key_down(GLFW_KEY_RIGHT_SHIFT)
            if keycode in GLFW_TO_GLYPH_NAME[STATE.shift_pressed]:
                STATE.user_inputs.append(GLFW_TO_GLYPH_NAME[STATE.shift_pressed][keycode])
                return
            
            if keycode >= GLFW_KEY_A and keycode <= GLFW_KEY_Z:
                # caps lock - shift - result
                # True      - True  - lowercase
                # True      - False - uppercase
                # False     - True  - uppercase
                # False     - False - lowercase
                if STATE.caps_lock_on == STATE.shift_pressed:
                    keycode += 32
                    
            if keycode not in NON_DRAWABLE_KEYS:
                STATE.user_inputs.append(chr(keycode))

def is_points_clockwise(points: list[rl.Vector2]):
    if len(points) == 2:
        p0, p1 = points
        is_counter_clockwise = False
        if p0.y >= p1.y:
            if p0.y == p1.y:
                is_counter_clockwise = p0.x > p1.x
            else:
                is_counter_clockwise = True
        return not is_counter_clockwise

    area = 0

    for i in range(len(points)):
        v1 = points[i]
        v2 = points[(i+1) % len(points)]
        area += (v2.x - v1.x) * (v2.y + v1.y)
    
    return area > 0

def is_clockwise(curves: list[list[rl.Vector2]]):
    points: list[rl.Vector2] = []
    are_clockwise = []
    for curve in curves:
        points.append(curve[0])
        is_cw = is_points_clockwise(curve)
        are_clockwise.append(is_cw)
    return is_points_clockwise(points), are_clockwise


def update_single_glyph(glyph, hmtx_for_key, global_translate_x, global_translate_y) -> rl.Rectangle:
    scaling_factor = STATE.scaling_factor

    def transform(pair: tuple[int, int]) -> rl.Vector2:
        p1x, p1y = pair
        x, y = global_translate_x + p1x//scaling_factor, global_translate_y-p1y//scaling_factor
        return rl.Vector2(x, y)

    def transform_contour(contour: GlyphContour):
        vs = list(map(lambda segment: list(map(transform, segment)), contour.segments))
        contour.segment_vectors = vs
        is_cw, are_clockwise = is_clockwise(vs)
        contour.is_clockwise = is_cw
        contour.segment_directions = are_clockwise
    
    if "components" in glyph:
        glyph_contours = handle_compound_glyphs(glyph)
    elif "coordinates" in glyph:
        glyph_contours = all_contour_segments(glyph)
    else:
        advance_width, _ = hmtx_for_key
        advance_width = advance_width // scaling_factor
        bounding_box = rl.Rectangle(1, 1, advance_width, 1)
        STATE.glyph_boundaries.append(bounding_box)
        STATE.outline_segments.append([])
        return bounding_box

    font_width, font_height, boundaries = find_char_width_height(glyph)
    
    for contour in glyph_contours:
        transform_contour(contour)

    STATE.outline_segments.append(glyph_contours)

    x_min, y_min, x_max, y_max = boundaries

    minv = transform((x_min, y_min))
    maxv = transform((x_max, y_max))

    bounding_box = rl.Rectangle(
        int(minv.x), int(maxv.y),
        font_width // scaling_factor, font_height // scaling_factor
    )

    STATE.glyph_boundaries.append(bounding_box)

    return bounding_box


def update():
    # clear the lists
    STATE.outline_segments = []
    STATE.glyph_boundaries = []

    global_translate_x = 100
    global_translate_y = int(rl.get_screen_height() * 0.80)
    total_width = 0
    
    for key in STATE.user_inputs:
        if key == "phont_newline":
            global_translate_x = 0
            global_translate_y += int(rl.get_screen_height() * 0.13)
            total_width = 0
            continue
        
        glyph = glyf_table[key].__dict__
        hmtx_for_key = hmtx.__dict__['metrics'][key]
        bounding_box = update_single_glyph(glyph, hmtx_for_key, global_translate_x, global_translate_y)
        total_width += bounding_box.width
        
        if rl.get_screen_width() < total_width:
            STATE.glyph_boundaries.pop(-1)
            STATE.outline_segments.pop(-1)
            total_width -= bounding_box.width
            global_translate_x = 0
            global_translate_y += int(rl.get_screen_height() * 0.13)
            bounding_box = update_single_glyph(glyph, hmtx_for_key, global_translate_x, global_translate_y)
            total_width = bounding_box.width
        
        global_translate_x += bounding_box.width

    STATE.base_y = global_translate_y

def sign(value):
    if value == 0:
        return 0
    return -1 if value < 0 else 1

from time import time

def render_glyph():
    start = time()
    rl.begin_drawing()
    rl.clear_background(rl.BLACK)

    if STATE.draw_bounding_box:
        for gb in STATE.glyph_boundaries:
            rl.draw_rectangle_lines_ex(gb, 1.0, rl.BLUE)

    for glyph_id, contours in enumerate(STATE.outline_segments):
        gb = STATE.glyph_boundaries[glyph_id]

        for ry in range(int(gb.y), int(gb.y + gb.height)):
            # if ry != 512:
            #     continue

            pixel = rl.Vector2(gb.x, ry)
            dots: list[tuple[rl.Vector2, list[rl.Vector2]]] = []
            dots_h: list[tuple[rl.Vector2, list[rl.Vector2]]] = []
            for contour in contours:
                for segment in contour.segment_vectors:
                    if len(segment) == 2:
                        res = check_if_intersects_line(*segment, pixel)
                    else:
                        res = check_if_intersects_bezier(*segment, pixel)
                    
                    if len(res) == 3:
                        for v in res:
                            if v is None: continue
                            dots_h.append((v, segment, 1))
                    else:
                        for v in res:
                            dots.append((v, segment, len(res)))
            
            dots.extend(dots_h)

            def dots_key(data):
                dot = data[0]
                if isinstance(dot, tuple):
                    return dot[0].x
                return dot.x

            dots.sort(key=dots_key)
            
            i = 0
            is_odd = True
            while i < len(dots) - 1:
                a, b = dots[i], dots[i+1]
                pa, edge_a, num_intersect_a = a
                pb, edge_b, num_intersect_b = b

                if isinstance(pa, tuple):
                    if isinstance(pb, tuple):
                        rl.draw_line_v(pa[0], pb[1], rl.GREEN)
                    else:
                        rl.draw_line_v(pa[0], pb, rl.GREEN)
                    i += 1
                    continue

                if isinstance(pb, tuple):
                    rl.draw_line_v(pa, pb[1], rl.GREEN)
                    i += 1
                    continue
 
                if pa.x == pb.x:
                    result = set(filter(
                        lambda v: v != 0,
                        map(lambda v: sign(pa.y - v.y), [edge_a[0], edge_a[-1], edge_b[0], edge_b[-1]])
                    ))
                    # basically
                    # if both curves are on the same side of the scanline -> count twice (odd -> even -> odd)
                    # if each curve lies on different sides of the scanline -> count one (odd -> even)
                    #   - having +1 intersections with the scanline automatically means that lines are not on the same side
                    #   - otherwise we take the non-intersected points from edges, 
                    #     take the distance from the intersection point and check if the values have the same sign or not
                    #     having the same sign indicates that they are on the same side
                    if len(result) == 2 or (num_intersect_a > 1 or num_intersect_b > 1):
                        is_odd = not is_odd

                if is_odd:
                    rl.draw_line_v(pa, pb, rl.GREEN)

                # def pront(inp):
                #     k, edge, _ = inp
                #     l = "".join(list(map(lambda z: f"[{round(z.x, ndigits=3)},{round(z.y, ndigits=3)}]", edge)))
                #     return f"{round(k.x, ndigits=3)} - {l}"

                # print(list(map(pront, [a, b])), "draw" if is_odd else "skip")

                # rl.draw_rectangle_v(pa, rl.Vector2(1,1), rl.MAGENTA)          
                # rl.draw_rectangle_v(pb, rl.Vector2(1,1), rl.MAGENTA)          

                is_odd = not is_odd
                i += 1
            print("----")

        i = 0
        while i < len(dots_h) and False:
            a, b = dots_h[i], dots_h[i+1]
            pa, edge_a, num_intersect_a = a
            pb, edge_b, num_intersect_b = b

            rl.draw_line_v(pa, pb, rl.GREEN)

            def pront(inp):
                    k, edge, _ = inp
                    l = "".join(list(map(lambda z: f"[{round(z.x, ndigits=3)},{round(z.y, ndigits=3)}]", edge)))
                    return f"{round(k.x, ndigits=3)} - {l}"

            print(list(map(pront, [a, b])))
            
            i += 2

        # draw the outline
        for contour in contours:
            for xx, segment in enumerate(contour.segment_vectors):
                # if not (xx == 28 or xx == 29):
                    # continue
                if len(segment) == 2:
                    s, e = segment
                    # rl.draw_line_ex(s, e, 4, rl.PURPLE)
                else:
                    continue
        #         else:
                    rl.draw_spline_bezier_quadratic(segment, 3, 1, rl.WHITE)

                # rl.draw_text(f"{xx}", int((segment[0].x + segment[-1].x) / 2) + 10, int((segment[0].y + segment[-1].y) / 2), 4, rl.WHITE)
                # rl.draw_text(f"{xx}", int((segment[0].x + segment[-1].x) / 2) + 10, int((segment[0].y + segment[-1].y) / 2), 4, rl.WHITE)

                # rl.draw_rectangle_v(segment[0], rl.Vector2(1, 1), rl.BLUE)
                # rl.draw_rectangle_v(segment[-1], rl.Vector2(1, 1), rl.BLUE)

                # rl.draw_text(f"{segment[0].y}", int(segment[0].x) - 10, int(segment[0].y), 4, rl.WHITE)
                # rl.draw_text(f"{segment[-1].y}", int(segment[-1].x) - 10, int(segment[-1].y), 4, rl.WHITE)

                rl.draw_circle_v(segment[0], 2, rl.BLUE)
                rl.draw_circle_v(segment[-1], 2, rl.BLUE)
    total = time() - start

    print(total)

    if STATE.draw_base_line:
        rl.draw_line(0, STATE.base_y, rl.get_screen_width(), STATE.base_y, rl.RED)
    rl.end_drawing()

if __name__ == "__main__":
    rl.init_window(0, 0, "font-rendering")
    rl.set_target_fps(30)
    rl.toggle_fullscreen()
    
    while not rl.window_should_close():
        grab_user_input()
        update()
        render_glyph()
        
    rl.close_window()