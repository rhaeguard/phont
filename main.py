from typing import Any, Self, Dict
import time
from fontTools.ttLib import TTFont
import pyray as rl
from raylib import ffi
from glfw_constants import *
from bezier import *

# Open the TTF file
# font = TTFont("./assets/EBGaramond/EBGaramond-Regular.ttf")
font = TTFont("./assets/Fira_Code/static/FiraCode-Regular.ttf")

# Access the glyph table
glyf_table = font["glyf"]

# hmtx contains the advance width for characters that have no contour like space
hmtx = font["hmtx"]

ASCENT = font['hhea'].__dict__['ascent']
UNIT_PER_EM = font['head'].__dict__['unitsPerEm']
MAGIC_FACTOR = 96 / 72 # 72 point font is 1 logical inches tall; 96 is the number of dots per logical inch

# close the font file
font.close()

# key => (glyph_contours, dimensions)
GLYPH_CONTOUR_CACHE: Dict[str, tuple[list['GlyphContour'], tuple[int, int, list[int, int, int, int]]]] = dict()


TIMES_BENCHMARK = {
    "update": [],
    "rendered_glyph_count": (0, 0)
}

class GlyphBoundary:
    def __init__(self, x: float, y: float, width: float, height: float) -> None:
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.rect = rl.Rectangle(x, y, width, height)
        self.advance_width = None
        self.lsb = None

    @property
    def rsb(self):
        return self.advance_width - self.width - self.lsb

    def em_square_width(self):
        return self.lsb + self.width + self.rsb

    def calculate_shader_properties(self, contours: list['GlyphContour']):
        len_contours_ref = ffi.new("int*")
        len_contours_ref[0] = len(contours)
        
        polyline_max_count = max((len(c.polylines) for c in contours), default=-1) + 1 # +1 because we append the last element to the end of the list
        if polyline_max_count == 0:
            self.skip = True
            return

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

        self.offset = rl.Vector2(int(self.x), int(self.y))
        self.count_contour = len_contours_ref
        self.count_polyline = len_polyline_max_count_ref
        self.polylines = all_polylines
        self.polylines_length = len(all_polylines)
        self.skip = False


class GlyphContour:
    def __init__(
        self,
        segments: list[list[tuple[int, int]]]
    ) -> None:
        self.segments = segments
        self.polylines: list[rl.Vector2] = []

    def copy(self) -> Self:
        return GlyphContour(self.segments)


class ProgramState:
    # draw flags
    draw_bounding_box = False
    draw_base_line = False
    draw_outline = False
    draw_filled_font = True

    # glyph content related
    outline_segments: list[list[GlyphContour]] = []
    glyph_boundaries: list['GlyphBoundary'] = []

    # sizing and alignment
    font_size_in_pts = 16 # not really that robust: https://learn.microsoft.com/en-us/windows/win32/learnwin32/dpi-and-device-independent-pixels
    scaling_factor = 1
    line_spacing: float = None
    base_y: int = -1
    offset_y: float = 0.0
    # screen border info, related to scrolling
    border_top_y: float = 0.0
    text_height: float = None
    
    # user input
    user_inputs: list[str] = []
    shift_pressed: bool = False
    caps_lock_on: bool = False
    mouse_wheel_move: float = 0.0

    # misc
    texture: rl.Texture = None


STATE = None


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
    # font_width, font_height, boundaries
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
    STATE.mouse_wheel_move = rl.get_mouse_wheel_move()

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
    key, advance_width, global_translate_x, global_translate_y
) -> GlyphBoundary:
    scaling_factor = STATE.scaling_factor

    def transform(pair: tuple[int, int], x_min: int) -> rl.Vector2:
        p1x, p1y = pair
        p1x = p1x - x_min
        x, y = (
            global_translate_x + p1x * scaling_factor,
            global_translate_y - p1y * scaling_factor,
        )
        y += STATE.offset_y
        return rl.Vector2(x, y)

    def transform_contour(contour: GlyphContour, x_min: int):
        vs = list(map(lambda segment: list(map(lambda s: transform(s, x_min), segment)), contour.segments))
        contour.polylines = generate_polylines(vs)
    
    if key not in GLYPH_CONTOUR_CACHE:
        bounding_box = GlyphBoundary(1, 1, advance_width, 1)
        STATE.glyph_boundaries.append(bounding_box)
        STATE.outline_segments.append([])
        return bounding_box
    
    cached_contours, dimensions = GLYPH_CONTOUR_CACHE[key]

    glyph_contours = [c.copy() for c in cached_contours]
    
    font_width, font_height, boundaries = dimensions
    x_min, y_min, x_max, y_max = boundaries

    for contour in glyph_contours:
        transform_contour(contour, x_min)

    STATE.outline_segments.append(glyph_contours)

    minv = transform((x_min, y_min), x_min)
    maxv = transform((x_max, y_max), x_min)

    bounding_box = GlyphBoundary(
        minv.x,
        maxv.y,
        font_width * scaling_factor,
        font_height * scaling_factor,
    )

    STATE.glyph_boundaries.append(bounding_box)

    return bounding_box


def update():
    TIME_START_BENCH = time.monotonic()
    # clear the lists
    STATE.outline_segments = []
    STATE.glyph_boundaries = []

    global_translate_x = 0
    global_translate_y = STATE.line_spacing

    min_y_allowed = float(rl.get_screen_height()) - STATE.text_height
    STATE.offset_y += STATE.mouse_wheel_move * 400 * rl.get_frame_time() #TODO: play around with the scroll speed
    STATE.offset_y = rl.clamp(STATE.offset_y, min_y_allowed, 0.0)

    total_width = 0

    for key in STATE.user_inputs:
        if key == "phont_newline":
            global_translate_x = 0
            global_translate_y += STATE.line_spacing
            total_width = 0
            continue

        hmtx_for_key = hmtx.__dict__["metrics"][key]
        
        advance_width, left_side_bearing = hmtx_for_key
        left_side_bearing = left_side_bearing * STATE.scaling_factor
        advance_width = advance_width * STATE.scaling_factor

        global_translate_x += left_side_bearing
        bounding_box = update_single_glyph(
            key, advance_width, global_translate_x, global_translate_y
        )
        
        bounding_box.advance_width = advance_width
        bounding_box.lsb = left_side_bearing

        total_width += bounding_box.em_square_width()

        if rl.get_screen_width() < total_width:
            STATE.glyph_boundaries.pop(-1)
            STATE.outline_segments.pop(-1)
            global_translate_x = left_side_bearing
            global_translate_y += STATE.line_spacing
            bounding_box = update_single_glyph(
                key, advance_width, global_translate_x, global_translate_y
            )
            bounding_box.advance_width = advance_width
            bounding_box.lsb = left_side_bearing
            total_width = bounding_box.em_square_width()

        # clipping the glyph outside of the screen
        if bounding_box.y > rl.get_screen_height():
            STATE.glyph_boundaries.pop(-1)
            STATE.outline_segments.pop(-1)
            break

        if bounding_box.y + bounding_box.height < 0:
            STATE.glyph_boundaries.pop(-1)
            STATE.outline_segments.pop(-1)
            global_translate_x -= left_side_bearing
            continue

        global_translate_x += (bounding_box.width + bounding_box.rsb)

    STATE.text_height = (STATE.user_inputs.count("phont_newline") + 1) * STATE.line_spacing * 1.2 # * 1.2 # this is to have some whitespace at the bottom

    for glyph_id, contours in enumerate(STATE.outline_segments):
        gb: GlyphBoundary = STATE.glyph_boundaries[glyph_id]
        if STATE.draw_filled_font:
            gb.calculate_shader_properties(contours)

    STATE.base_y = global_translate_y

    TIMES_BENCHMARK["update"].append(
        time.monotonic() - TIME_START_BENCH
    )
    TIMES_BENCHMARK["rendered_glyph_count"] = (len(STATE.glyph_boundaries))

def render_glyph(shader, polylines_location, count_contour_location, count_polyline_location, offset_location):
    rl.begin_drawing()
    rl.clear_background(rl.BLACK)

    if STATE.draw_bounding_box:
        for gb in STATE.glyph_boundaries:
            rl.draw_rectangle_lines_ex(gb.rect, 1.0, rl.BLUE)
            xmin = int(gb.x - gb.lsb)
            ymin = int(gb.y)
            rl.draw_rectangle_lines(
                xmin, ymin, int(gb.advance_width), int(gb.height), rl.GREEN
            )

    for glyph_id, contours in enumerate(STATE.outline_segments):
        gb = STATE.glyph_boundaries[glyph_id]

        if STATE.draw_filled_font:
            if gb.skip:
                continue

            rl.set_shader_value(shader, offset_location, gb.offset, rl.ShaderUniformDataType.SHADER_UNIFORM_VEC2)
            rl.set_shader_value(shader, count_contour_location, gb.count_contour, rl.ShaderUniformDataType.SHADER_UNIFORM_INT)
            rl.set_shader_value(shader, count_polyline_location, gb.count_polyline, rl.ShaderUniformDataType.SHADER_UNIFORM_INT)
            rl.set_shader_value_v(shader, polylines_location, gb.polylines, rl.ShaderUniformDataType.SHADER_UNIFORM_VEC2, gb.polylines_length)

            rl.begin_shader_mode(shader)

            source = rl.Rectangle(0, 0, gb.width+1, gb.height+1) # +1 because we wanna draw the bottom and right parts correctly, it clamps them if we don't add +something_positive_int
            rl.draw_texture_rec(STATE.texture, source, rl.Vector2(gb.x, gb.y), rl.WHITE)

            rl.end_shader_mode()
                        
        # draw the outline
        if STATE.draw_outline:
            for contour in contours:
                for pi in range(len(contour.polylines)):
                    s, e = contour.polylines[pi], contour.polylines[(pi+1)%len(contour.polylines)]
                    rl.draw_line_v(s, e, rl.GREEN)
                    rl.draw_circle_v(s, 0.5, rl.RED)
                    rl.draw_circle_v(e, 0.5, rl.RED)


    if STATE.draw_base_line:
        rl.draw_line(0, STATE.base_y, rl.get_screen_width(), STATE.base_y, rl.RED)
    
    rl.end_drawing()


def prepopulate_glyph_cache():
    inputs = []
    for _, v in CHAR_TO_GLYPH_NAME.items():
        inputs.append(v)

    for ch in range(65, 91):
        inputs.append(chr(ch))
        inputs.append(chr(ch+32))
    
    for key in inputs:
        glyph = glyf_table[key].__dict__
        if "components" in glyph:
            glyph_contours = handle_compound_glyphs(glyph)
        elif "coordinates" in glyph:
            glyph_contours = all_contour_segments(glyph)
        else:
            print(f"[WARN] unprocessable glyph for char[{key}]")
            continue

        GLYPH_CONTOUR_CACHE[key] = (glyph_contours, find_char_width_height(glyph_contours))

if __name__ == "__main__":
    STATE = ProgramState()

    prepopulate_glyph_cache()

    # with open("shader.frag") as file:
    with open("main.py") as file:
        for line in file:
            for ch in line:
                if ch == '\n':
                    user_input = "phont_newline"
                elif ch == '\t':
                    user_input = "space"
                elif ch == '\r':
                    continue
                else:
                    if ch in CHAR_TO_GLYPH_NAME:
                        user_input = CHAR_TO_GLYPH_NAME[ch]
                    else:
                        user_input = ch
                STATE.user_inputs.append(user_input)

    rl.set_trace_log_level(rl.TraceLogLevel.LOG_ERROR)
    rl.set_config_flags(rl.ConfigFlags.FLAG_VSYNC_HINT)
    rl.init_window(0, 0, "font-rendering")
    rl.set_target_fps(30)
    rl.toggle_fullscreen()

    texture_img = rl.gen_image_color(rl.get_screen_width(), rl.get_screen_height(), rl.WHITE)
    texture = rl.load_texture_from_image(texture_img)
    rl.unload_image(texture_img)

    STATE.texture = texture
    STATE.scaling_factor = (STATE.font_size_in_pts * MAGIC_FACTOR * rl.get_window_scale_dpi().x) / UNIT_PER_EM # assumption here is that the scaling dpi factor is constant across both dimensions
    STATE.line_spacing = ASCENT * STATE.scaling_factor * 1.2
    STATE.text_height = float(rl.get_screen_height())

    shader = rl.load_shader(None, "shader.frag")
    polylines_location = rl.get_shader_location(shader, "polylines")
    count_contour_location = rl.get_shader_location(shader, "count_contour")
    count_polyline_location = rl.get_shader_location(shader, "count_polyline")
    offset_location = rl.get_shader_location(shader, "offset")

    while not rl.window_should_close():
        grab_user_input()
        update()
        render_glyph(shader, polylines_location, count_contour_location, count_polyline_location, offset_location)

        print(sum(TIMES_BENCHMARK["update"]) / len(TIMES_BENCHMARK["update"]), TIMES_BENCHMARK["rendered_glyph_count"])

    rl.unload_texture(STATE.texture)

    rl.close_window()
