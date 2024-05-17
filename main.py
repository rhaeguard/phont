from typing import Any
from fontTools.ttLib import TTFont
import pyray as rl
from raylib import ffi
from glfw_constants import *
from bezier import *

# Open the TTF file
# font = TTFont("./assets/EBGaramond/EBGaramond-Regular.ttf")
font = TTFont("./assets/arial.ttf")

# Access the glyph table
glyf_table = font["glyf"]
# hmtx contains the advance width for characters that have no contour like space
hmtx = font["hmtx"]

UNIT_PER_EM = font['head'].__dict__['unitsPerEm']
MAGIC_FACTOR = 96 / 72 # 72 point font is 1 logical inches tall; 96 is the number of dots per logical inch

# close the font file
font.close()

class GlyphContour:
    def __init__(
        self,
        segments: list[list[tuple[int, int]]]
    ) -> None:
        self.segments = segments
        self.polylines: list[rl.Vector2] = []


class ProgramState:
    draw_bounding_box = False
    draw_base_line = False
    draw_outline = not True
    draw_filled_font = True
    font_size_in_pts = 32 # not really that robust: https://learn.microsoft.com/en-us/windows/win32/learnwin32/dpi-and-device-independent-pixels
    scaling_factor = 1
    outline_segments: list[list[GlyphContour]] = []
    glyph_boundaries: list[rl.Rectangle] = []
    base_y: int = -1
    user_inputs: list[str] = []
    text_centered: bool = False
    shift_pressed: bool = False
    caps_lock_on: bool = False
    texture: rl.Texture = None


STATE = ProgramState()


def find_char_width_height(glyph_contours: list[GlyphContour]) -> tuple[int, int, list[int, int, int, int]]:
    """
    required for translation
    """
    x_min, x_max, y_min, y_max = float("Inf"), float("-Inf"), float("Inf"), float("-Inf")
    for c in glyph_contours:
        for segment in c.segments:
            for v in segment:
                x_min = min(x_min, v[0])
                x_max = max(x_max, v[0])
                y_min = min(y_min, v[1])
                y_max = max(y_max, v[1])
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

                    for x in range(1, len(segment) - 2):
                        c1, c2 = segment[x], segment[x + 1]
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
                    for x in range(0, point_count - 1, 2):
                        pts = expanded_segment[x : x + 3]
                        all_segments.append(pts)
                else:
                    all_segments.append(segment)
                i -= 1  # go back because the end dot is actually shared between curves
                break
            i += 1
        i += 1
    return all_segments


def handle_compound_glyphs(glyph: dict[str, Any]) -> list[GlyphContour]:
    all_components = glyph["components"]

    result: list[GlyphContour] = []
    for component in all_components:
        glyph_name, transformation = component.getComponentInfo()
        g = glyf_table[glyph_name].__dict__
        result.extend(all_contour_segments(g))

    return result


def all_contour_segments(glyph: dict[str, Any]) -> list[GlyphContour]:
    coords = list(glyph["coordinates"])
    flags = list(glyph["flags"])
    # endPtsOfContours contains indices that indicate the end of a contour
    # these are useful to extract out however many contours a particular glyph has
    end_of_contours = list(glyph["endPtsOfContours"])

    all_contours: list[GlyphContour] = []
    start = 0
    for end in end_of_contours:
        segment_coords = coords[start : end + 1]
        segment_coords = segment_coords + [
            segment_coords[0]
        ]  # include the first entry to close the loop

        segment_flags = flags[start : end + 1]
        segment_flags = segment_flags + [
            segment_flags[0]
        ]  # include the first entry to close the loop

        all_segments_in_contour = segments(segment_coords, segment_flags)
        contour = GlyphContour(segments=all_segments_in_contour)
        all_contours.append(contour)
        start = end + 1
    return all_contours


def grab_user_input():
    while (keycode := rl.get_key_pressed()) != 0:
        if keycode == GLFW_KEY_BACKSPACE:
            # it's backspace
            if len(STATE.user_inputs) > 0:
                STATE.user_inputs.pop()
        elif keycode == GLFW_KEY_CAPS_LOCK:
            STATE.caps_lock_on = not STATE.caps_lock_on
        elif keycode == GLFW_KEY_ENTER:
            STATE.user_inputs.append("phont_newline")
        else:
            STATE.shift_pressed = rl.is_key_down(GLFW_KEY_LEFT_SHIFT) or rl.is_key_down(
                GLFW_KEY_RIGHT_SHIFT
            )
            if keycode in GLFW_TO_GLYPH_NAME[STATE.shift_pressed]:
                STATE.user_inputs.append(
                    GLFW_TO_GLYPH_NAME[STATE.shift_pressed][keycode]
                )
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


def should_skip_segment(data: list[rl.Vector2], pixel: rl.Vector2) -> bool:
    y_min = data[0].y
    y_max = data[0].y
    x_max = data[0].x
    for v in data:
        y_min = min(y_min, v.y)
        y_max = max(y_max, v.y)
        x_max = max(x_max, v.x)
    return y_min > pixel.y or y_max < pixel.y or x_max < pixel.x

def generate_polylines(bezier_curves: list[list[rl.Vector2]]) -> list[rl.Vector2]:
    polygon_vertices: list[rl.Vector2] = []
    for curve in bezier_curves:
        if len(curve) == 2:
            polygon_vertices.extend(curve)
        else:
            curve_lines = produce_bezier_lines(*curve)
            polygon_vertices.extend(curve_lines) 
    
    deduped = [polygon_vertices[0]]

    for i, v in enumerate(polygon_vertices):
        if i == 0:
            continue
        last = deduped[-1]
        if v.x == last.x and v.y == last.y:
            continue
        else:
            deduped.append(v)
    
    return deduped

def update_single_glyph(
    glyph, hmtx_for_key, global_translate_x, global_translate_y
) -> rl.Rectangle:
    scaling_factor = STATE.scaling_factor

    def transform(pair: tuple[int, int]) -> rl.Vector2:
        p1x, p1y = pair
        x, y = (
            global_translate_x + p1x * scaling_factor,
            global_translate_y - p1y * scaling_factor,
        )
        return rl.Vector2(x, y)

    def transform_contour(contour: GlyphContour):
        vs = list(map(lambda segment: list(map(transform, segment)), contour.segments))
        contour.polylines = generate_polylines(vs)

    if "components" in glyph:
        glyph_contours = handle_compound_glyphs(glyph)
    elif "coordinates" in glyph:
        glyph_contours = all_contour_segments(glyph)
    else:
        advance_width, _ = hmtx_for_key
        advance_width = advance_width * scaling_factor
        bounding_box = rl.Rectangle(1, 1, advance_width, 1)
        STATE.glyph_boundaries.append(bounding_box)
        STATE.outline_segments.append([])
        return bounding_box

    font_width, font_height, boundaries = find_char_width_height(glyph_contours)

    for contour in glyph_contours:
        transform_contour(contour)

    STATE.outline_segments.append(glyph_contours)

    x_min, y_min, x_max, y_max = boundaries

    minv = transform((x_min, y_min))
    maxv = transform((x_max, y_max))

    bounding_box = rl.Rectangle(
        int(minv.x),
        int(maxv.y),
        font_width * scaling_factor,
        font_height * scaling_factor,
    )

    STATE.glyph_boundaries.append(bounding_box)

    return bounding_box


def update():
    # clear the lists
    STATE.outline_segments = []
    STATE.glyph_boundaries = []

    global_translate_x = 0
    global_translate_y = int(rl.get_screen_height() * 0.20)
    total_width = 0

    for key in STATE.user_inputs:
        if key == "phont_newline":
            global_translate_x = 0
            global_translate_y += int(rl.get_screen_height() * 0.20)
            total_width = 0
            continue

        glyph = glyf_table[key].__dict__
        hmtx_for_key = hmtx.__dict__["metrics"][key]
        bounding_box = update_single_glyph(
            glyph, hmtx_for_key, global_translate_x, global_translate_y
        )
        total_width += bounding_box.width

        if rl.get_screen_width() < total_width:
            STATE.glyph_boundaries.pop(-1)
            STATE.outline_segments.pop(-1)
            total_width -= bounding_box.width
            global_translate_x = 0
            global_translate_y += int(rl.get_screen_height() * 0.20)
            bounding_box = update_single_glyph(
                glyph, hmtx_for_key, global_translate_x, global_translate_y
            )
            total_width = bounding_box.width

        global_translate_x += bounding_box.width

    STATE.base_y = global_translate_y

def render_glyph(shader):
    rl.begin_drawing()
    rl.clear_background(rl.BLACK)

    if STATE.draw_bounding_box:
        for gb in STATE.glyph_boundaries:
            rl.draw_rectangle_lines_ex(gb, 1.0, rl.BLUE)

    polylines_location = rl.get_shader_location(shader, "polylines")
    count_contour_location = rl.get_shader_location(shader, "count_contour")
    count_polyline_location = rl.get_shader_location(shader, "count_polyline")
    offset_location = rl.get_shader_location(shader, "offset")

    for glyph_id, contours in enumerate(STATE.outline_segments):
        gb = STATE.glyph_boundaries[glyph_id]

        if STATE.draw_filled_font:
            len_contours_ref = ffi.new("int*")
            len_contours_ref[0] = len(contours)
            
            polyline_max_count = max((len(c.polylines) for c in contours), default=-1) + 1 # +1 because we append the last element to the end of the list
            if polyline_max_count == 0:
                continue

            len_polyline_max_count_ref = ffi.new("int*")
            len_polyline_max_count_ref[0] = polyline_max_count

            total_polylines = polyline_max_count * len(contours)
            all_polylines = ffi.new(f"Vector2[{total_polylines}]")
            i = 0
            for contour in contours:
                new_p = contour.polylines
                remains = polyline_max_count - len(new_p) - 1
                new_p = new_p + [new_p[0]] + ([rl.Vector2(int(-666), int(-666))] * remains)
                for p in new_p:
                    all_polylines[i] = p
                    i+=1

            rl.set_shader_value(shader, offset_location, rl.Vector2(int(gb.x), int(gb.y)), rl.ShaderUniformDataType.SHADER_UNIFORM_VEC2)
            rl.set_shader_value(shader, count_contour_location, len_contours_ref, rl.ShaderUniformDataType.SHADER_UNIFORM_INT)
            rl.set_shader_value(shader, count_polyline_location, len_polyline_max_count_ref, rl.ShaderUniformDataType.SHADER_UNIFORM_INT)
            rl.set_shader_value_v(shader, polylines_location, all_polylines, rl.ShaderUniformDataType.SHADER_UNIFORM_VEC2, len(all_polylines))

            rl.begin_shader_mode(shader)

            source = rl.Rectangle(0, 0, gb.width, gb.height)
            rl.draw_texture_rec(STATE.texture, source, rl.Vector2(gb.x, gb.y), rl.WHITE)

            rl.end_shader_mode()
                        
        # draw the outline
        if STATE.draw_outline:
            for contour in contours:
                for pi in range(len(contour.polylines)-1):
                    s, e = contour.polylines[pi], contour.polylines[pi+1]
                    rl.draw_line_v(s, e, rl.GREEN)
                    rl.draw_circle_v(s, 2, rl.WHITE)
                    rl.draw_circle_v(e, 2, rl.WHITE)


    if STATE.draw_base_line:
        rl.draw_line(0, STATE.base_y, rl.get_screen_width(), STATE.base_y, rl.RED)
    
    rl.end_drawing()


if __name__ == "__main__":
    rl.init_window(0, 0, "font-rendering")
    rl.set_target_fps(30)
    rl.toggle_fullscreen()

    texture_img = rl.gen_image_color(rl.get_screen_width(), rl.get_screen_height(), rl.WHITE)
    texture = rl.load_texture_from_image(texture_img)
    rl.unload_image(texture_img)

    STATE.texture = texture
    STATE.scaling_factor = (STATE.font_size_in_pts * MAGIC_FACTOR * rl.get_window_scale_dpi().x) / UNIT_PER_EM # assumption here is that the scaling dpi factor is constant across both dimensions

    shader = rl.load_shader(None, "shader.frag")

    while not rl.window_should_close():
        grab_user_input()
        update()
        render_glyph(shader)

    rl.unload_texture(STATE.texture)

    rl.close_window()
