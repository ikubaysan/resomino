import pygame
import sys
import random
from typing import List, Tuple, Optional, Dict, Callable, Union

pygame.init()

# ---------------------------------------------------
# Window and Board Settings
# ---------------------------------------------------
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700
GRID_WIDTH = 10   # Tetris: 10 columns
GRID_HEIGHT = 20  # Tetris: 20 rows
BLOCK_SIZE = 30   # Each cell is 30x30 pixels (single-player layout)

# Single-player board placement
BOARD_X = (WINDOW_WIDTH - GRID_WIDTH * BLOCK_SIZE) // 2
BOARD_Y = 60
HOLD_AREA_X = 20
HOLD_AREA_Y = 80
NEXT_AREA_X = WINDOW_WIDTH - 150
NEXT_AREA_Y = 80
NUM_NEXT_PIECES = 6

# ---------------------------------------------------
# Timing (everything is in SECONDS and driven by delta time)
# ---------------------------------------------------
# FPS is only a render cap. The simulation is advanced in small fixed-size
# slices (MAX_SIM_STEP) per rendered frame, so the game plays the same at
# 20 FPS, 60 FPS or 240 FPS. A single very long frame (window drag, lag spike)
# is clamped to MAX_FRAME_TIME so the game doesn't "teleport" forward.
FPS = 60
MAX_SIM_STEP = 1.0 / 120.0
MAX_FRAME_TIME = 0.25

GRAVITY_INTERVAL = 0.5     # seconds per row of natural gravity (SDF multiplies this)
LOCK_DELAY = 0.5
MAX_LOCK_RESETS = 15
ENTRY_DELAY = 0.05         # short pause after a piece spawns. This is the
                           # "between pieces" window used by IRS / IHS buffering.
HARD_DROP_LOCKOUT = 0.2    # "Prevent Accidental Hard Drops" window after a natural lock
SD_PRIORITY_MIN_SDF = 40   # what counts as a "very high" soft drop speed
SPAWN_BUFFER_ROWS = 4     # hidden rows above the visible field a piece may occupy
TEST_FAIL_DELAY = 1.2      # how long the settings test shows "topped out" before resetting

# ---------------------------------------------------
# Versus-mode layout (two boards, smaller blocks)
# ---------------------------------------------------
VS_BLOCK_SIZE = 22
VS_BOARD_W = GRID_WIDTH * VS_BLOCK_SIZE
VS_BOARD_H = GRID_HEIGHT * VS_BLOCK_SIZE
VS_BOARD_Y = 130
VS_P1_BOARD_X = 150
VS_P2_BOARD_X = WINDOW_WIDTH - 150 - VS_BOARD_W
VS_NUM_NEXT = 4

# ---------------------------------------------------
# Tetromino Definitions
# ---------------------------------------------------
# Super Rotation System (SRS) -- the standard used by TETR.IO, Puyo Puyo Tetris
# and every Guideline game. Each rotation state is the piece's cells inside its
# bounding box (3x3 for J/L/S/T/Z, 4x4 for I and O), listed in the order
# 0 = spawn, 1 = rotated right (CW), 2 = 180, 3 = rotated left (CCW).
# Coordinates are (x, y) with y increasing downward.
TETROMINOES = {
    "I": [
        [(0, 1), (1, 1), (2, 1), (3, 1)],
        [(2, 0), (2, 1), (2, 2), (2, 3)],
        [(0, 2), (1, 2), (2, 2), (3, 2)],
        [(1, 0), (1, 1), (1, 2), (1, 3)],
    ],
    "O": [
        [(1, 0), (2, 0), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (2, 1)],
    ],
    "T": [
        [(1, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (1, 2)],
        [(1, 0), (0, 1), (1, 1), (1, 2)],
    ],
    "S": [
        [(1, 0), (2, 0), (0, 1), (1, 1)],
        [(1, 0), (1, 1), (2, 1), (2, 2)],
        [(1, 1), (2, 1), (0, 2), (1, 2)],
        [(0, 0), (0, 1), (1, 1), (1, 2)],
    ],
    "Z": [
        [(0, 0), (1, 0), (1, 1), (2, 1)],
        [(2, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (1, 2), (2, 2)],
        [(1, 0), (0, 1), (1, 1), (0, 2)],
    ],
    "L": [
        [(2, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 2)],
        [(0, 1), (1, 1), (2, 1), (0, 2)],
        [(0, 0), (1, 0), (1, 1), (1, 2)],
    ],
    "J": [
        [(0, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (0, 2), (1, 2)],
    ],
}

# Spawn row of each piece's bounding box. The I piece's cells sit on the 2nd row
# of its 4x4 box, so its box starts one row higher to put it on the top row.
SPAWN_Y: Dict[str, int] = {"I": -1}

# SRS wall kick tests, written the way the SRS charts are (x right, y UP).
# Key = (from_state, to_state). Each test is tried in order; the first one that
# fits is used. (The code flips y when applying them.) O never kicks.
_KICKS_JLSTZ = {
    (0, 1): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (1, 0): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
    (1, 2): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
    (2, 1): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (2, 3): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
    (3, 2): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (3, 0): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (0, 3): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
}
_KICKS_I = {
    (0, 1): [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
    (1, 0): [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
    (1, 2): [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
    (2, 1): [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
    (2, 3): [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
    (3, 2): [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
    (3, 0): [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
    (0, 3): [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
}


def srs_kicks(shape: str, from_state: int, to_state: int) -> List[Tuple[int, int]]:
    """Kick offsets as (dx, dy) in screen coordinates (y down)."""
    if shape == "O":
        return [(0, 0)]
    table = _KICKS_I if shape == "I" else _KICKS_JLSTZ
    return [(dx, -dy) for dx, dy in table[(from_state, to_state)]]


COLORS: Dict[str, Tuple[int, int, int]] = {
    "I": (0, 255, 255),
    "O": (255, 255, 0),
    "T": (128, 0, 128),
    "S": (0, 255, 0),
    "Z": (255, 0, 0),
    "J": (0, 0, 255),
    "L": (255, 165, 0),
}
GHOST_COLOR = (100, 100, 100)
GARBAGE_COLOR = (110, 110, 110)

# ---------------------------------------------------
# Controls
# ---------------------------------------------------
DEFAULT_CONTROLS: Dict[str, int] = {
    "left": pygame.K_LEFT,
    "right": pygame.K_RIGHT,
    "soft_drop": pygame.K_DOWN,
    "hard_drop": pygame.K_UP,
    "rotate_cw": pygame.K_x,
    "rotate_ccw": pygame.K_z,
    "hold": pygame.K_SPACE,
    "pause": pygame.K_p,
}

# Fixed control scheme for a local human "Player 2" in versus mode.
DEFAULT_CONTROLS_P2: Dict[str, int] = {
    "left": pygame.K_a,
    "right": pygame.K_d,
    "soft_drop": pygame.K_s,
    "hard_drop": pygame.K_w,
    "rotate_cw": pygame.K_e,
    "rotate_ccw": pygame.K_q,
    "hold": pygame.K_LSHIFT,
    "pause": pygame.K_ESCAPE,
}

ACTION_ORDER = [
    "left", "right", "soft_drop", "hard_drop",
    "rotate_cw", "rotate_ccw", "hold", "pause",
]
# Actions the game itself understands (pause is handled by the App).
INPUT_ACTIONS = [
    "left", "right", "soft_drop", "hard_drop",
    "rotate_cw", "rotate_ccw", "hold",
]
ACTION_LABELS: Dict[str, str] = {
    "left": "Move Left",
    "right": "Move Right",
    "soft_drop": "Soft Drop",
    "hard_drop": "Hard Drop",
    "rotate_cw": "Rotate CW",
    "rotate_ccw": "Rotate CCW",
    "hold": "Hold Piece",
    "pause": "Pause",
}

# ---------------------------------------------------
# Handling settings (configured per player; the CPU uses the settings of
# whichever player slot it occupies: P1 = left board, P2 = right board)
# ---------------------------------------------------
HANDLING_DEFAULTS: Dict[str, object] = {
    "arr": 33,     # ms per automatic repeat movement
    "das": 167,    # ms before automatic repeat starts
    "dcd": 17,     # ms DAS pauses after a rotate / drop
    "sdf": 6,      # soft drop gravity multiplier
    "prevent_accidental_hd": True,
    "cancel_das_on_dir_change": False,
    "sd_priority": True,
    "irs": "tap",
    "ihs": "tap",
}

# "slow" is the value at the LEFT end of the slider, "fast" the RIGHT end.
HANDLING_SLIDERS: List[dict] = [
    {"key": "arr", "label": "ARR", "slow": 90, "fast": 0, "unit": "ms",
     "desc": "Automatic Repeat Rate: the speed at which tetrominoes move when holding down "
             "movement keys, measured in MS per movement."},
    {"key": "das", "label": "DAS", "slow": 350, "fast": 20, "unit": "ms",
     "desc": "Delayed Auto Shift: the time between the initial keypress and the start of its "
             "automatic repeat movement, measured in MS."},
    {"key": "dcd", "label": "DCD", "slow": 350, "fast": 0, "unit": "ms",
     "desc": "DAS Cut Delay: if not 0, any ongoing DAS movement will pause for a set amount of "
             "time after dropping/rotating a piece, measured in MS."},
    {"key": "sdf", "label": "SDF", "slow": 5, "fast": 50, "unit": "X",
     "desc": "Soft Drop Factor: the factor with which soft drops change the gravity speed."},
]
SLIDER_BY_KEY: Dict[str, dict] = {s["key"]: s for s in HANDLING_SLIDERS}

HANDLING_BOOLS: List[Tuple[str, str, str]] = [
    ("prevent_accidental_hd", "Prevent Accidental Hard Drops",
     "If enabled, when a piece locks on its own, the hard drop key becomes unavailable for a "
     "moment. This prevents accidental hard drops."),
    ("cancel_das_on_dir_change", "Cancel DAS When Changing Directions",
     "If enabled, DAS charge is cancelled when you change directions."),
    ("sd_priority", "Prefer Soft Drop Over Movement",
     "If enabled, at very high speeds soft drop will always take precedence over horizontal "
     "movement, for a more consistent game feel."),
]
BOOL_BY_KEY = {b[0]: b for b in HANDLING_BOOLS}

BUFFER_MODES = ["off", "hold", "tap"]
BUFFER_MODE_LABELS = {"off": "Off", "hold": "Hold", "tap": "Tap"}
HANDLING_BUFFERS: List[Tuple[str, str, Dict[str, str]]] = [
    ("irs", "Rotation Buffering (IRS)", {
        "off": "Don't allow any rotation inputs between pieces.",
        "hold": "The next piece rotates if the key is held at the time the piece spawns.",
        "tap": "The next piece rotates if any rotations are entered between pieces. "
               "Multiple inputs stack.",
    }),
    ("ihs", "Hold Buffering (IHS)", {
        "off": "Don't allow pressing Hold between pieces.",
        "hold": "The next piece is Held if the key is held at the time the piece spawns.",
        "tap": "The next piece is Held if any hold inputs are entered between pieces.",
    }),
]
BUFFER_BY_KEY = {b[0]: b for b in HANDLING_BUFFERS}


def slider_min_max(spec: dict) -> Tuple[int, int]:
    return min(spec["slow"], spec["fast"]), max(spec["slow"], spec["fast"])


def slider_fraction(spec: dict, value: int) -> float:
    """0.0 = slow end (left), 1.0 = fast end (right)."""
    return (value - spec["slow"]) / float(spec["fast"] - spec["slow"])


def slider_value_from_fraction(spec: dict, f: float) -> int:
    return int(round(spec["slow"] + f * (spec["fast"] - spec["slow"])))


def slider_step(spec: dict, value: int, steps: int) -> int:
    """Move `steps` whole numbers toward 'fast' (negative = toward 'slow')."""
    sign = 1 if spec["fast"] > spec["slow"] else -1
    lo, hi = slider_min_max(spec)
    return max(lo, min(hi, value + sign * steps))


def format_slider_value(spec: dict, value: int) -> str:
    return f"{value} ms" if spec["unit"] == "ms" else f"{value}X"


WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
DARK_GRAY = (40, 40, 40)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
RED = (220, 60, 60)
GREEN = (80, 220, 100)
ORANGE = (255, 165, 0)

# ---------------------------------------------------
# Difficulty presets for the CPU opponent
# ---------------------------------------------------
# 10 difficulty levels, built by interpolating between the "easiest" and
# "hardest" CPU settings.
#   think_time:      reaction delay before the CPU starts moving a new piece
#   action_interval:  delay between each individual decision step
#   mistake_chance:   probability the CPU picks a random (non-optimal) placement
#   use_hold:         whether the CPU is allowed to use the hold slot strategically
def _build_difficulties() -> Dict[int, Dict[str, float]]:
    EASIEST = {"think_time": 0.65, "action_interval": 0.18, "mistake_chance": 0.45}
    HARDEST = {"think_time": 0.04, "action_interval": 0.02, "mistake_chance": 0.0}
    levels: Dict[int, Dict[str, float]] = {}
    for level in range(1, 11):
        t = (level - 1) / 9.0  # 0.0 at level 1 .. 1.0 at level 10
        levels[level] = {
            "think_time": EASIEST["think_time"] + (HARDEST["think_time"] - EASIEST["think_time"]) * t,
            "action_interval": EASIEST["action_interval"] + (HARDEST["action_interval"] - EASIEST["action_interval"]) * t,
            "mistake_chance": EASIEST["mistake_chance"] + (HARDEST["mistake_chance"] - EASIEST["mistake_chance"]) * t,
            "use_hold": level >= 3,
        }
    return levels


DIFFICULTIES: Dict[int, Dict[str, float]] = _build_difficulties()
DIFFICULTY_ORDER: List[int] = list(range(1, 11))


def difficulty_label(level: int) -> str:
    return f"Level {level}"


def difficulty_description(level: int) -> str:
    if level <= 2:
        return "Very slow reactions, frequent mistakes"
    elif level <= 4:
        return "Slow, makes mistakes fairly often"
    elif level <= 6:
        return "Moderate speed, occasional mistakes"
    elif level <= 8:
        return "Fast, rarely makes mistakes"
    else:
        return "Near-instant reactions, essentially optimal play"


class Tetromino:
    def __init__(self, shape: str):
        self.shape: str = shape
        self.rotation_index: int = 0
        self.x: int = 3
        self.y: int = SPAWN_Y.get(shape, 0)
        self.color: Tuple[int, int, int] = COLORS[shape]

    def get_blocks(self) -> List[Tuple[int, int]]:
        rotation_variants = TETROMINOES[self.shape]
        coords = rotation_variants[self.rotation_index % len(rotation_variants)]
        return [(self.x + cx, self.y + cy) for (cx, cy) in coords]

    def rotate(self, direction: int) -> None:
        self.rotation_index = (self.rotation_index + direction) % len(TETROMINOES[self.shape])


# Default layout used by TetrisGame.draw() for single-player screens.
DEFAULT_LAYOUT = {
    "board_x": BOARD_X, "board_y": BOARD_Y, "block_size": BLOCK_SIZE,
    "hold_x": HOLD_AREA_X, "hold_y": HOLD_AREA_Y,
    "next_x": NEXT_AREA_X, "next_y": NEXT_AREA_Y, "num_next": NUM_NEXT_PIECES,
    "stats_x": HOLD_AREA_X, "stats_y": HOLD_AREA_Y + 130,
    "show_mode_label": True, "show_time": True,
    "label_text": None, "label_x": None, "label_y": None,
    "outline_color": WHITE, "mini_unit": BLOCK_SIZE // 2,
    "garbage_x": None,
}


class TetrisGame:
    """
    Holds all logic/state for a single round of Tetris. Has no event loop of
    its own -- callers drive it by calling handle_event()/update()/draw().

    All timing is delta-time based. Input is expressed as press()/release()
    of named actions, which is what both the keyboard (handle_event) and the
    CPU (AIController) use, so handling settings (ARR/DAS/DCD/SDF/buffering)
    apply identically to humans and CPUs.
    """

    def __init__(self, mode: str, controls: Dict[str, int],
                 multiplayer: bool = False, label: str = "",
                 handling: Optional[Dict[str, object]] = None,
                 ai_controlled: bool = False) -> None:
        self.mode = mode  # "sprint", "endless", "versus" or "test"
        self.line_target: Optional[int] = 40 if mode == "sprint" else None
        self.controls = controls
        self.handling: Dict[str, object] = dict(HANDLING_DEFAULTS)
        if handling:
            self.handling.update(handling)
        self.ai_controlled = ai_controlled

        self.board: List[List[Optional[Tuple[int, int, int]]]] = [
            [None] * GRID_WIDTH for _ in range(GRID_HEIGHT)
        ]
        self.lines_cleared = 0
        self.total_time = 0.0
        self.upcoming_pieces: List[Tetromino] = []
        self._generate_new_bag()
        self._generate_new_bag()
        self.held_piece: Optional[Tetromino] = None
        self.hold_used_this_turn: bool = False
        self.current_piece: Tetromino = self.upcoming_pieces.pop(0)

        self.drop_timer: float = 0.0
        self.drop_interval: float = GRAVITY_INTERVAL
        self.lock_timer: float = 0.0
        self.lock_resets: int = 0
        self.game_over: bool = False
        self.cleared: bool = False

        # ---- Input / handling state ----
        self.held: Dict[str, bool] = {a: False for a in INPUT_ACTIONS}
        self.h_dir = 0                 # active horizontal direction (-1, 0, 1)
        self.das_timer = 0.0
        self.das_charged = False
        self.arr_timer = 0.0
        self.dcd_timer = 0.0           # remaining DAS-cut pause
        self.auto_stop_x: Optional[int] = None   # CPU only: "release the key" column
        self.entry_timer = 0.0         # >0 while in the between-pieces window
        self.irs_buffer: List[int] = []
        self.ihs_pending = False
        self.hd_lockout = 0.0

        # ---- Multiplayer / garbage state ----
        self.multiplayer = multiplayer
        self.label = label
        self.pending_garbage: int = 0
        self.combo: int = -1
        self.back_to_back: bool = False
        self.garbage_callback: Optional[Callable[[int], None]] = None
        self.total_garbage_sent = 0
        self.total_garbage_received = 0

    # -----------------------------------------------
    # Setup helpers
    # -----------------------------------------------
    def _generate_new_bag(self) -> None:
        shapes = list(TETROMINOES.keys())
        random.shuffle(shapes)
        for shape in shapes:
            self.upcoming_pieces.append(Tetromino(shape))

    # -----------------------------------------------
    # Input
    # -----------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type not in (pygame.KEYDOWN, pygame.KEYUP):
            return
        for action in INPUT_ACTIONS:
            if event.key == self.controls[action]:
                if event.type == pygame.KEYDOWN:
                    self.press(action)
                else:
                    self.release(action)
                return

    def press(self, action: str) -> None:
        if self.game_over:
            return
        h = self.handling
        self.held[action] = True
        if action in ("rotate_cw", "rotate_ccw"):
            d = 1 if action == "rotate_cw" else -1
            if self.entry_timer > 0:
                if h["irs"] == "tap":
                    self.irs_buffer.append(d)       # stacks
            else:
                self.rotate_piece(d)
        elif action == "hold":
            if self.entry_timer > 0:
                if h["ihs"] == "tap":
                    self.ihs_pending = True
            else:
                self.hold_piece()
        elif action == "hard_drop":
            if h["prevent_accidental_hd"] and self.hd_lockout > 0:
                return
            self.hard_drop()
        elif action in ("left", "right"):
            self._press_direction(-1 if action == "left" else 1)
        elif action == "soft_drop":
            self.drop_timer = 0.0
            if self.entry_timer <= 0:
                self.soft_drop()

    def release(self, action: str) -> None:
        self.held[action] = False
        if action in ("left", "right"):
            d = -1 if action == "left" else 1
            if self.h_dir != d:
                return  # released a key that wasn't the active direction
            other = "right" if action == "left" else "left"
            self.arr_timer = 0.0
            if self.held[other]:
                self.h_dir = -d
                if self.handling["cancel_das_on_dir_change"]:
                    self.das_timer = 0.0
                    self.das_charged = False
            else:
                self.h_dir = 0
                self.das_timer = 0.0
                self.das_charged = False
        elif action == "soft_drop":
            self.drop_timer = 0.0

    def _press_direction(self, d: int) -> None:
        prev = self.h_dir
        self.h_dir = d
        if prev == 0:
            self.das_timer = 0.0
            self.das_charged = False
        elif prev != d and self.handling["cancel_das_on_dir_change"]:
            self.das_timer = 0.0
            self.das_charged = False
        # (changing direction without cancel keeps the current DAS charge)
        self.arr_timer = 0.0
        self.move_piece(dx=d)

    def _reconcile_keys(self, keys) -> None:
        """Drop 'held' flags for keys that are physically up (e.g. released
        while the game was paused and we never saw the KEYUP)."""
        for action in INPUT_ACTIONS:
            if self.held[action] and not keys[self.controls[action]]:
                self.release(action)

    def resync_held(self, keys) -> None:
        """Re-sync held keys after a pause/resume (no movement is triggered)."""
        if self.ai_controlled:
            return
        self._reconcile_keys(keys)
        for action, d in (("left", -1), ("right", 1)):
            if keys[self.controls[action]] and not self.held[action]:
                self.held[action] = True
                if self.h_dir == 0:
                    self.h_dir = d
                    self.das_timer = 0.0
                    self.das_charged = False
        if keys[self.controls["soft_drop"]]:
            self.held["soft_drop"] = True

    # -----------------------------------------------
    # Update (all delta-time based)
    # -----------------------------------------------
    def update(self, dt: float, keys=None) -> None:
        if self.game_over:
            return
        if keys is not None and not self.ai_controlled:
            self._reconcile_keys(keys)

        self.total_time += dt
        if self.hd_lockout > 0:
            self.hd_lockout = max(0.0, self.hd_lockout - dt)

        # Between-pieces window: gravity/lock are paused, buffers collect input.
        dt_rem = dt
        if self.entry_timer > 0:
            if self.entry_timer > dt:
                self.entry_timer -= dt
                dt_rem = 0.0
            else:
                dt_rem = dt - self.entry_timer
                self.entry_timer = 0.0
                self._finish_entry()
                if self.game_over:
                    return

        if self._sd_priority_active():
            self._update_gravity(dt_rem)
            if self.game_over:
                return
            self._update_horizontal(dt)
        else:
            self._update_horizontal(dt)
            self._update_gravity(dt_rem)

    def _sd_priority_active(self) -> bool:
        h = self.handling
        return bool(h["sd_priority"] and self.held["soft_drop"]
                    and h["sdf"] >= SD_PRIORITY_MIN_SDF and self.entry_timer <= 0)

    def _finish_entry(self) -> None:
        """The new piece becomes active: apply IHS first, then IRS."""
        h = self.handling
        buf = list(self.irs_buffer)
        self.irs_buffer.clear()
        if h["irs"] == "hold":
            if self.held["rotate_cw"]:
                buf = [1]
            elif self.held["rotate_ccw"]:
                buf = [-1]
        do_hold = ((h["ihs"] == "hold" and self.held["hold"])
                   or (h["ihs"] == "tap" and self.ihs_pending))
        self.ihs_pending = False
        if do_hold:
            self.hold_piece()
            if self.game_over:
                return
        for d in buf:
            self.rotate_piece(d)

    def _repeat_move(self, d: int) -> bool:
        if self.auto_stop_x is not None and self.current_piece.x == self.auto_stop_x:
            return False
        return self.move_piece(dx=d)

    def _update_horizontal(self, dt: float) -> None:
        # DCD pause counts down no matter what.
        pause_used = min(dt, self.dcd_timer)
        self.dcd_timer -= pause_used
        free_t = dt - pause_used  # portion of this step in which repeating may happen

        d = self.h_dir
        if d == 0:
            return
        h = self.handling
        das = h["das"] / 1000.0
        arr = h["arr"] / 1000.0

        if not self.das_charged:
            self.das_timer += dt
            if self.das_timer < das:
                return
            over = self.das_timer - das
            self.das_timer = das
            self.das_charged = True
            self.arr_timer = arr  # first repeat happens right when DAS completes
            free_t = min(over, free_t)

        if self.dcd_timer > 0:
            return
        if self._sd_priority_active() and not self.is_on_ground(self.current_piece):
            return

        if arr <= 0:
            for _ in range(GRID_WIDTH + 2):   # slide as far as possible
                if not self._repeat_move(d):
                    break
        else:
            self.arr_timer += free_t
            while self.arr_timer >= arr:
                self.arr_timer -= arr
                if not self._repeat_move(d):
                    self.arr_timer = arr      # blocked: retry as soon as possible
                    break
                if self.game_over:
                    break

    def _update_gravity(self, dt: float) -> None:
        if dt <= 0 or self.entry_timer > 0 or self.game_over:
            return
        piece = self.current_piece
        interval = self.drop_interval
        if self.held["soft_drop"]:
            interval = self.drop_interval / float(self.handling["sdf"])

        if self.is_on_ground(piece):
            self.lock_timer += dt
            self.drop_timer = 0.0
            if self.lock_timer >= LOCK_DELAY:
                self.lock_piece()
                if self.handling["prevent_accidental_hd"]:
                    self.hd_lockout = HARD_DROP_LOCKOUT
                self.spawn_new_piece()
            return

        self.lock_timer = 0.0
        self.drop_timer += dt
        while self.drop_timer >= interval:
            self.drop_timer -= interval
            old_y = piece.y
            piece.y += 1
            if not self._is_valid_position(piece):
                piece.y = old_y
                self.drop_timer = 0.0
                break
            if self.is_on_ground(piece):
                self._register_ground_touch()
                self.drop_timer = 0.0
                break

    def _cut_das(self) -> None:
        dcd = self.handling["dcd"]
        if dcd > 0:
            self.dcd_timer = dcd / 1000.0

    # -----------------------------------------------
    # Movement / rotation
    # -----------------------------------------------
    def _register_ground_touch(self) -> None:
        if self.lock_resets < MAX_LOCK_RESETS:
            self.lock_timer = 0.0
            self.lock_resets += 1

    def move_piece(self, dx: int = 0, dy: int = 0) -> bool:
        old_x, old_y = self.current_piece.x, self.current_piece.y
        self.current_piece.x += dx
        self.current_piece.y += dy
        if not self._is_valid_position(self.current_piece):
            self.current_piece.x, self.current_piece.y = old_x, old_y
            return False
        moved = (self.current_piece.x, self.current_piece.y) != (old_x, old_y)
        if moved and self.is_on_ground(self.current_piece):
            self._register_ground_touch()
        return True

    def rotate_piece(self, direction: int) -> None:
        """SRS rotation: try the rotation in place, then each SRS kick in order."""
        piece = self.current_piece
        old_rotation = piece.rotation_index
        old_x, old_y = piece.x, piece.y
        new_rotation = (old_rotation + direction) % 4
        piece.rotation_index = new_rotation
        for dx, dy in srs_kicks(piece.shape, old_rotation, new_rotation):
            piece.x = old_x + dx
            piece.y = old_y + dy
            if self._is_valid_position(piece):
                break
        else:
            piece.rotation_index = old_rotation
            piece.x, piece.y = old_x, old_y
            return
        if self.is_on_ground(piece):
            self._register_ground_touch()
        self._cut_das()

    def soft_drop(self) -> None:
        old_y = self.current_piece.y
        self.current_piece.y += 1
        if not self._is_valid_position(self.current_piece):
            self.current_piece.y = old_y
            return
        if self.is_on_ground(self.current_piece):
            self._register_ground_touch()

    def hard_drop(self) -> None:
        while self._is_valid_position(self.current_piece):
            self.current_piece.y += 1
        self.current_piece.y -= 1
        self.lock_piece()
        self.spawn_new_piece()

    def hold_piece(self) -> None:
        if self.hold_used_this_turn:
            return
        if self.held_piece is None:
            self.held_piece = self.current_piece
            self.spawn_new_piece()
            self.entry_timer = 0.0      # holding doesn't add another entry window
            self.irs_buffer.clear()
            self.ihs_pending = False
        else:
            temp = self.current_piece
            self.current_piece = self.held_piece
            self.held_piece = temp
            if not self._place_at_spawn(self.current_piece):
                self.game_over = True
        self.hold_used_this_turn = True
        self.drop_timer = 0.0
        self.lock_timer = 0.0
        self.lock_resets = 0

    def _place_at_spawn(self, piece: Tetromino) -> bool:
        """Put a piece at the spawn column. If the stack is in the way, try
        successively higher (hidden) rows above the top line so the player
        can still try to move it somewhere safe. Only fails if no spot works."""
        piece.x = 3
        piece.rotation_index = 0
        base_y = SPAWN_Y.get(piece.shape, 0)
        for offset in range(0, -SPAWN_BUFFER_ROWS, -1):
            piece.y = base_y + offset
            if self._is_valid_position(piece):
                return True
        piece.y = base_y
        return False

    def spawn_new_piece(self) -> None:
        if self.game_over:
            return
        if self.multiplayer:
            self._apply_pending_garbage()
            if self.game_over:
                return
        if len(self.upcoming_pieces) < 7:
            self._generate_new_bag()
        self.current_piece = self.upcoming_pieces.pop(0)
        self.hold_used_this_turn = False
        self.drop_timer = 0.0
        self.lock_timer = 0.0
        self.lock_resets = 0
        self.entry_timer = ENTRY_DELAY
        self.irs_buffer.clear()
        self.ihs_pending = False
        self._cut_das()
        if not self._place_at_spawn(self.current_piece):
            self.game_over = True

    def lock_piece(self) -> None:
        locked_above_top = False
        for x, y in self.current_piece.get_blocks():
            if y < 0:
                locked_above_top = True
            elif y < GRID_HEIGHT and 0 <= x < GRID_WIDTH:
                self.board[y][x] = self.current_piece.color
        self.clear_lines()
        if locked_above_top:
            self.game_over = True
            return
        if self.line_target is not None and self.lines_cleared >= self.line_target:
            self.cleared = True
            self.game_over = True

    def clear_lines(self) -> int:
        full_rows = []
        for row_idx in range(GRID_HEIGHT):
            if all(self.board[row_idx][col_idx] is not None for col_idx in range(GRID_WIDTH)):
                full_rows.append(row_idx)
        for row_idx in full_rows:
            del self.board[row_idx]
            self.board.insert(0, [None for _ in range(GRID_WIDTH)])
        n = len(full_rows)
        self.lines_cleared += n
        if self.multiplayer:
            self._process_attack(n)
        return n

    # -----------------------------------------------
    # Garbage / attack handling (multiplayer only)
    # -----------------------------------------------
    @staticmethod
    def _combo_bonus(combo: int) -> int:
        table = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]
        if combo < 0:
            return 0
        return table[combo] if combo < len(table) else 5

    def _process_attack(self, n: int) -> None:
        if n == 0:
            self.combo = -1
            return
        self.combo += 1
        base = {1: 0, 2: 1, 3: 2, 4: 4}.get(n, 4)
        is_tetris = (n == 4)
        b2b_bonus = 0
        if is_tetris:
            if self.back_to_back:
                b2b_bonus = 1
            self.back_to_back = True
        else:
            self.back_to_back = False
        attack = base + b2b_bonus + self._combo_bonus(self.combo)
        if attack <= 0:
            return
        if self.pending_garbage > 0:
            cancel = min(self.pending_garbage, attack)
            self.pending_garbage -= cancel
            attack -= cancel
        if attack > 0:
            self.total_garbage_sent += attack
            if self.garbage_callback:
                self.garbage_callback(attack)

    def add_garbage(self, n: int) -> None:
        if n > 0:
            self.pending_garbage += n
            self.total_garbage_received += n

    def _apply_pending_garbage(self) -> None:
        if self.pending_garbage <= 0:
            return
        n = self.pending_garbage
        self.pending_garbage = 0
        gap_col = random.randint(0, GRID_WIDTH - 1)
        for _ in range(n):
            if any(cell is not None for cell in self.board[0]):
                self.game_over = True
                break
            del self.board[0]
            self.board.append(
                [None if col == gap_col else GARBAGE_COLOR for col in range(GRID_WIDTH)]
            )

    def _is_valid_position(self, piece: Tetromino) -> bool:
        for x, y in piece.get_blocks():
            if x < 0 or x >= GRID_WIDTH or y >= GRID_HEIGHT or y < -SPAWN_BUFFER_ROWS:
                return False
            if y >= 0 and self.board[y][x] is not None:
                return False
        return True

    def is_on_ground(self, piece: Tetromino) -> bool:
        for x, y in piece.get_blocks():
            if y + 1 >= GRID_HEIGHT or (y + 1 >= 0 and self.board[y + 1][x] is not None):
                return True
        return False

    # -----------------------------------------------
    # Drawing
    # -----------------------------------------------
    def draw(self, screen: pygame.Surface, font_small: pygame.font.Font,
             font_med: pygame.font.Font, layout: Optional[dict] = None) -> None:
        if layout is None:
            layout = DEFAULT_LAYOUT
        bs = layout["block_size"]
        bx, by = layout["board_x"], layout["board_y"]

        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                cell_color = self.board[y][x]
                rect = pygame.Rect(bx + x * bs, by + y * bs, bs, bs)
                if cell_color:
                    pygame.draw.rect(screen, cell_color, rect)
                    pygame.draw.rect(screen, WHITE, rect, 1)
                else:
                    pygame.draw.rect(screen, DARK_GRAY, rect, 1)

        self._draw_ghost_piece(screen, layout)

        # Blocks above the top line are drawn above the board so you can see them.
        for x, y in self.current_piece.get_blocks():
            rect = pygame.Rect(bx + x * bs, by + y * bs, bs, bs)
            pygame.draw.rect(screen, self.current_piece.color, rect)
            pygame.draw.rect(screen, WHITE, rect, 1)

        board_rect = pygame.Rect(bx, by, GRID_WIDTH * bs, GRID_HEIGHT * bs)
        pygame.draw.rect(screen, layout.get("outline_color", WHITE), board_rect, 2)

        if layout.get("garbage_x") is not None:
            self._draw_garbage_bar(screen, layout["garbage_x"], by, GRID_HEIGHT * bs, bs, font_small)

        if layout.get("label_text"):
            label_surf = font_med.render(layout["label_text"], True, layout.get("outline_color", WHITE))
            screen.blit(label_surf, (layout["label_x"], layout["label_y"]))

        self._draw_hold_area(screen, font_small, layout)
        self._draw_next_pieces(screen, font_small, layout)
        self._draw_stats(screen, font_small, layout)

    def _draw_ghost_piece(self, screen: pygame.Surface, layout: dict) -> None:
        bs = layout["block_size"]
        bx, by = layout["board_x"], layout["board_y"]
        ghost = Tetromino(self.current_piece.shape)
        ghost.x = self.current_piece.x
        ghost.y = self.current_piece.y
        ghost.rotation_index = self.current_piece.rotation_index
        while self._is_valid_position(ghost):
            ghost.y += 1
        ghost.y -= 1
        for (x, y) in ghost.get_blocks():
            if y >= 0:
                rect = pygame.Rect(bx + x * bs, by + y * bs, bs, bs)
                pygame.draw.rect(screen, GHOST_COLOR, rect)
                pygame.draw.rect(screen, WHITE, rect, 1)

    def _draw_garbage_bar(self, screen, x, y, board_height_px, bs, font_small) -> None:
        bar_w = max(10, bs // 2)
        max_show = GRID_HEIGHT - 1
        shown = min(self.pending_garbage, max_show)
        pygame.draw.rect(screen, WHITE, (x - 1, y - 1, bar_w + 2, board_height_px + 2), 1)
        for i in range(shown):
            seg_h = board_height_px / max_show
            seg_y = y + board_height_px - (i + 1) * seg_h
            rect = pygame.Rect(x, seg_y, bar_w, max(2, seg_h - 2))
            pygame.draw.rect(screen, RED, rect)
        if self.pending_garbage > 0:
            count_surf = font_small.render(str(self.pending_garbage), True, RED)
            screen.blit(count_surf, (x - 4, y - 22))

    def _draw_mini_piece(self, screen, shape, color, offset_x, offset_y, unit) -> None:
        coords = TETROMINOES[shape][0]
        min_x = min(cx for cx, _ in coords)
        min_y = min(cy for _, cy in coords)
        for cx, cy in coords:
            rx = offset_x + (cx - min_x) * unit
            ry = offset_y + (cy - min_y) * unit
            rect = pygame.Rect(rx, ry, unit, unit)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, WHITE, rect, 1)

    def _draw_hold_area(self, screen, font, layout) -> None:
        text_surf = font.render("HOLD", True, WHITE)
        screen.blit(text_surf, (layout["hold_x"], layout["hold_y"] - 22))
        if self.held_piece:
            unit = layout.get("mini_unit", BLOCK_SIZE // 2)
            self._draw_mini_piece(screen, self.held_piece.shape, self.held_piece.color,
                                  layout["hold_x"] + 5, layout["hold_y"] + 6, unit)

    def _draw_next_pieces(self, screen, font, layout) -> None:
        text_surf = font.render("NEXT", True, WHITE)
        screen.blit(text_surf, (layout["next_x"], layout["next_y"] - 22))
        num_next = layout.get("num_next", NUM_NEXT_PIECES)
        unit = layout.get("mini_unit", BLOCK_SIZE // 2)
        spacing = unit * 2 + 15
        for i in range(num_next):
            if i < len(self.upcoming_pieces):
                piece = self.upcoming_pieces[i]
                offset_x = layout["next_x"]
                offset_y = layout["next_y"] + (i * spacing)
                self._draw_mini_piece(screen, piece.shape, piece.color, offset_x, offset_y, unit)

    def _draw_stats(self, screen, font, layout) -> None:
        sx, sy = layout["stats_x"], layout["stats_y"]
        if self.line_target is not None:
            lines_str = f"Lines: {min(self.lines_cleared, self.line_target)}/{self.line_target}"
        else:
            lines_str = f"Lines: {self.lines_cleared}"
        lines_text = font.render(lines_str, True, WHITE)
        row = 0
        if layout.get("show_mode_label", True):
            mode_label = {"sprint": "40-Line Sprint", "endless": "Endless Mode",
                          "test": "Handling Test",
                          "versus": self.label or "Versus"}.get(self.mode, "")
            mode_text = font.render(mode_label, True, (180, 180, 180))
            screen.blit(mode_text, (sx, sy + row * 26))
            row += 1
        screen.blit(lines_text, (sx, sy + row * 26))
        row += 1
        if layout.get("show_time", True):
            minutes = int(self.total_time // 60)
            seconds = int(self.total_time % 60)
            millis = int((self.total_time * 100) % 100)
            time_text = font.render(f"Time: {minutes}:{seconds:02d}.{millis:02d}", True, WHITE)
            screen.blit(time_text, (sx, sy + row * 26))
            row += 1
        if self.multiplayer:
            atk_text = font.render(f"Sent: {self.total_garbage_sent}", True, (200, 160, 160))
            screen.blit(atk_text, (sx, sy + row * 26))


# ---------------------------------------------------
# CPU opponent
# ---------------------------------------------------
class AIController:
    """
    Drives a TetrisGame the same way a human would: it looks at the board,
    decides on a target (rotation, column, whether to hold), and then
    presses/releases the same virtual keys a human would. That means the
    CPU's player slot handling settings (ARR, DAS, DCD, SDF, buffering,
    etc.) apply to it exactly as they would to a person.

    Difficulty (1-10) still controls reaction time, decision pace and
    mistake rate. All timing is delta-time based.
    """

    def __init__(self, game: TetrisGame, difficulty: int):
        self.game = game
        settings = DIFFICULTIES.get(difficulty, DIFFICULTIES[5])
        self.think_time = settings["think_time"]
        self.action_interval = settings["action_interval"]
        self.mistake_chance = settings["mistake_chance"]
        self.use_hold_enabled = settings["use_hold"]

        self._target_piece = None
        self._target: Optional[dict] = None
        self._think_timer = 0.0
        self._action_timer = 0.0
        self._piece_time = 0.0
        self._hold_committed = False
        self._holding = 0   # direction key the CPU is currently holding (-1/0/1)

    def update(self, dt: float) -> None:
        game = self.game
        if game.game_over:
            return

        if game.current_piece is not self._target_piece:
            self._release_dirs()
            self._target_piece = game.current_piece
            self._target = self._decide_target()
            self._think_timer = 0.0
            self._action_timer = 0.0
            self._piece_time = 0.0
            self._hold_committed = False

        self._think_timer += dt
        self._piece_time += dt
        # Wait out the reaction time and the between-pieces window.
        if self._think_timer < self.think_time or game.entry_timer > 0:
            return
        self._action_timer += dt
        if self._action_timer < self.action_interval:
            return
        self._action_timer = 0.0
        self._step()

    def _tap(self, action: str) -> None:
        self.game.press(action)
        self.game.release(action)

    def _release_dirs(self) -> None:
        if self._holding != 0:
            self.game.release("left" if self._holding < 0 else "right")
            self._holding = 0
        self.game.auto_stop_x = None

    def _step(self) -> None:
        game = self.game
        target = self._target
        if target is None:
            self._release_dirs()
            self._tap("hard_drop")
            return

        # Safety valve: never let the CPU stall indefinitely.
        if self._piece_time > self.think_time + 2.0 + 20 * self.action_interval:
            self._release_dirs()
            self._tap("hard_drop")
            return

        if target["use_hold"] and not self._hold_committed:
            self._release_dirs()
            self._tap("hold")
            self._hold_committed = True
            self._target_piece = game.current_piece  # don't re-plan after our own hold
            return

        cur = game.current_piece
        if cur.rotation_index != target["rotation"]:
            self._tap("rotate_cw")
            return

        want = target["x"]
        if cur.x != want:
            d = 1 if want > cur.x else -1
            if self._holding != d:
                self._release_dirs()
                game.auto_stop_x = want   # like a player letting go at the right column
                game.press("right" if d > 0 else "left")
                self._holding = d
            return  # DAS / ARR move the piece; keep holding

        self._release_dirs()
        self._tap("hard_drop")

    # -----------------------------------------------
    # Placement search
    # -----------------------------------------------
    def _all_placements(self, shape: str) -> List[Tuple[float, int, int]]:
        results: List[Tuple[float, int, int]] = []
        board = self.game.board
        variants = TETROMINOES[shape]
        seen_rotations = set()
        for rot in range(4):
            coords = tuple(variants[rot])
            if coords in seen_rotations:
                continue
            seen_rotations.add(coords)
            min_x = min(c[0] for c in coords)
            max_x = max(c[0] for c in coords)
            for x in range(-min_x, GRID_WIDTH - max_x):
                def fits(yy, _coords=coords, _x=x):
                    for cx, cy in _coords:
                        bx, by = _x + cx, yy + cy
                        if bx < 0 or bx >= GRID_WIDTH or by >= GRID_HEIGHT:
                            return False
                        if by >= 0 and board[by][bx] is not None:
                            return False
                    return True

                y = min(0, self.game.current_piece.y)
                if not fits(y):
                    continue
                while fits(y + 1):
                    y += 1
                score = self._score_placement(coords, x, y)
                results.append((score, rot, x))
        return results

    def _evaluate_piece_best(self, shape: str) -> Tuple[float, int, int]:
        placements = self._all_placements(shape)
        if not placements:
            return (float("-inf"), 0, 3)
        return max(placements, key=lambda t: t[0])

    def _score_placement(self, coords, x, y) -> float:
        board = self.game.board
        temp = [row[:] for row in board]
        for cx, cy in coords:
            bx, by = x + cx, y + cy
            if by < 0:
                return -1000.0   # would lock out above the top line
            if by < GRID_HEIGHT and 0 <= bx < GRID_WIDTH:
                temp[by][bx] = True
        lines_cleared = 0
        remaining_rows = []
        for row in temp:
            if all(cell is not None for cell in row):
                lines_cleared += 1
            else:
                remaining_rows.append(row)
        for _ in range(lines_cleared):
            remaining_rows.insert(0, [None] * GRID_WIDTH)
        temp = remaining_rows
        heights = [0] * GRID_WIDTH
        holes = 0
        for col in range(GRID_WIDTH):
            found = False
            for row in range(GRID_HEIGHT):
                if temp[row][col] is not None:
                    if not found:
                        heights[col] = GRID_HEIGHT - row
                        found = True
                elif found:
                    holes += 1
        agg_height = sum(heights)
        bumpiness = sum(abs(heights[i] - heights[i + 1]) for i in range(GRID_WIDTH - 1))
        return (
            -0.510066 * agg_height
            + 0.760666 * lines_cleared
            - 0.35663 * holes
            - 0.184483 * bumpiness
        )

    def _decide_target(self) -> dict:
        game = self.game
        current_shape = game.current_piece.shape
        best_current = self._evaluate_piece_best(current_shape)

        can_hold = self.use_hold_enabled and not game.hold_used_this_turn
        alt_shape = None
        best_alt = None
        if can_hold:
            if game.held_piece is not None:
                alt_shape = game.held_piece.shape
            elif game.upcoming_pieces:
                alt_shape = game.upcoming_pieces[0].shape
            if alt_shape:
                best_alt = self._evaluate_piece_best(alt_shape)

        use_hold = False
        chosen = best_current
        chosen_shape = current_shape
        if best_alt is not None and best_alt[0] > best_current[0] + 0.01:
            use_hold = True
            chosen = best_alt
            chosen_shape = alt_shape

        if random.random() < self.mistake_chance:
            placements = self._all_placements(chosen_shape)
            if placements:
                chosen = random.choice(placements)
                if use_hold and random.random() < 0.5:
                    use_hold = False
                    chosen_shape = current_shape
                    fallback = self._all_placements(chosen_shape)
                    if fallback:
                        chosen = random.choice(fallback)

        score, rot, x = chosen
        return {"use_hold": use_hold, "rotation": rot, "x": x}


# ---------------------------------------------------
# Versus match: two TetrisGames wired together with garbage
# ---------------------------------------------------
class VersusMatch:
    """
    opponent:
      "human"       -> both boards are locally controlled (P1 controls + fixed P2 controls)
      "cpu"         -> P1 is human, P2 is CPU. difficulty is a single int level (1-10)
      "cpu_vs_cpu"  -> both boards are CPU-controlled. difficulty is a (int, int) tuple

    handling_p1 / handling_p2 are the Handling settings for the left / right
    board. CPUs use the settings of the slot they occupy.
    """

    def __init__(self, p1_controls: Dict[str, int], opponent: str,
                 difficulty: Optional[Union[int, Tuple[int, int]]] = None,
                 handling_p1: Optional[Dict[str, object]] = None,
                 handling_p2: Optional[Dict[str, object]] = None):
        self.opponent = opponent
        self.difficulty = difficulty
        self.ai1: Optional[AIController] = None
        self.ai2: Optional[AIController] = None

        if opponent == "cpu_vs_cpu":
            d1, d2 = difficulty
            self.p1 = TetrisGame(mode="versus", controls=p1_controls, multiplayer=True,
                                 label=f"CPU A ({difficulty_label(d1)})",
                                 handling=handling_p1, ai_controlled=True)
            self.p2 = TetrisGame(mode="versus", controls=DEFAULT_CONTROLS_P2, multiplayer=True,
                                 label=f"CPU B ({difficulty_label(d2)})",
                                 handling=handling_p2, ai_controlled=True)
            self.ai1 = AIController(self.p1, d1)
            self.ai2 = AIController(self.p2, d2)
        elif opponent == "cpu":
            self.p1 = TetrisGame(mode="versus", controls=p1_controls, multiplayer=True,
                                 label="Player 1", handling=handling_p1)
            self.p2 = TetrisGame(mode="versus", controls=DEFAULT_CONTROLS_P2, multiplayer=True,
                                 label=f"CPU ({difficulty_label(difficulty)})",
                                 handling=handling_p2, ai_controlled=True)
            self.ai2 = AIController(self.p2, difficulty)
        else:  # "human"
            self.p1 = TetrisGame(mode="versus", controls=p1_controls, multiplayer=True,
                                 label="Player 1", handling=handling_p1)
            self.p2 = TetrisGame(mode="versus", controls=DEFAULT_CONTROLS_P2, multiplayer=True,
                                 label="Player 2", handling=handling_p2)

        self.p1.garbage_callback = self.p2.add_garbage
        self.p2.garbage_callback = self.p1.add_garbage
        self.finished = False
        self.winner: Optional[str] = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.ai1 is None:
            self.p1.handle_event(event)
        if self.ai2 is None:
            self.p2.handle_event(event)

    def resync_held(self, keys) -> None:
        self.p1.resync_held(keys)
        self.p2.resync_held(keys)

    def update(self, dt: float, keys) -> None:
        if self.finished:
            return
        if self.ai1 is not None:
            self.ai1.update(dt)
        self.p1.update(dt, keys)
        if self.ai2 is not None:
            self.ai2.update(dt)
        self.p2.update(dt, keys)

        if self.p1.game_over or self.p2.game_over:
            self.finished = True
            if self.p1.game_over and self.p2.game_over:
                self.winner = "Draw"
            elif self.p1.game_over:
                self.winner = self.p2.label
            else:
                self.winner = self.p1.label

    def _layout(self, board_x: int, outline_color, label_text: str, garbage_x: int,
                hold_x: int, next_x: int) -> dict:
        return {
            "board_x": board_x, "board_y": VS_BOARD_Y, "block_size": VS_BLOCK_SIZE,
            "hold_x": hold_x, "hold_y": VS_BOARD_Y - 55,
            "next_x": next_x, "next_y": VS_BOARD_Y, "num_next": VS_NUM_NEXT,
            "stats_x": board_x, "stats_y": VS_BOARD_Y + VS_BOARD_H + 12,
            "show_mode_label": False, "show_time": True,
            "label_text": label_text, "label_x": board_x, "label_y": VS_BOARD_Y - 90,
            "outline_color": outline_color, "mini_unit": 12,
            "garbage_x": garbage_x,
        }

    def draw(self, screen: pygame.Surface, font_small, font_med, font_big) -> None:
        screen.fill(BLACK)
        p1_layout = self._layout(
            VS_P1_BOARD_X, CYAN, self.p1.label,
            garbage_x=VS_P1_BOARD_X - 18,
            hold_x=VS_P1_BOARD_X, next_x=VS_P1_BOARD_X + VS_BOARD_W + 20,
        )
        p2_layout = self._layout(
            VS_P2_BOARD_X, ORANGE, self.p2.label,
            garbage_x=VS_P2_BOARD_X + VS_BOARD_W + 4,
            hold_x=VS_P2_BOARD_X, next_x=VS_P2_BOARD_X - 70,
        )
        self.p1.draw(screen, font_small, font_med, p1_layout)
        self.p2.draw(screen, font_small, font_med, p2_layout)

        vs_surf = font_big.render("VS", True, WHITE)
        screen.blit(vs_surf, ((WINDOW_WIDTH - vs_surf.get_width()) // 2, VS_BOARD_Y + VS_BOARD_H // 2 - 20))

        if self.finished:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            if self.winner == "Draw":
                text = "DRAW!"
            else:
                text = f"{self.winner} WINS!"
            win_surf = font_big.render(text, True, YELLOW)
            screen.blit(win_surf, ((WINDOW_WIDTH - win_surf.get_width()) // 2, 260))
            prompt = font_med.render("Enter: Rematch    Esc: Main Menu", True, WHITE)
            screen.blit(prompt, ((WINDOW_WIDTH - prompt.get_width()) // 2, 330))


# ---------------------------------------------------
# Settings screen layout
# ---------------------------------------------------
SET_ROW_Y0 = 78
SET_ROW_GAP = 38
SET_LABEL_X = 60
SET_TRACK_X = 430
SET_TRACK_W = 300


class App:
    """
    Top-level state machine driving the single pygame event loop. Handles
    the title screen, main menu, controls remapping, handling settings
    (with a live test mode), single-player games, and the versus flow.
    """

    STATE_TITLE = "TITLE"
    STATE_MENU = "MENU"
    STATE_CONTROLS = "CONTROLS"
    STATE_SETTINGS = "SETTINGS"
    STATE_SETTINGS_TEST = "SETTINGS_TEST"
    STATE_VERSUS_MENU = "VERSUS_MENU"
    STATE_DIFFICULTY_MENU = "DIFFICULTY_MENU"
    STATE_DIFFICULTY_MENU_2 = "DIFFICULTY_MENU_2"
    STATE_PLAYING = "PLAYING"
    STATE_PAUSED = "PAUSED"
    STATE_GAME_OVER = "GAME_OVER"
    STATE_PLAYING_VS = "PLAYING_VS"
    STATE_PAUSED_VS = "PAUSED_VS"
    STATE_VS_OVER = "VS_OVER"

    def __init__(self) -> None:
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Tetris")
        self.clock = pygame.time.Clock()

        self.font_title = pygame.font.SysFont("Arial", 64, bold=True)
        self.font_big = pygame.font.SysFont("Arial", 36, bold=True)
        self.font_med = pygame.font.SysFont("Arial", 26)
        self.font_small = pygame.font.SysFont("Arial", 20)
        self.font_tiny = pygame.font.SysFont("Arial", 16)

        self.controls: Dict[str, int] = dict(DEFAULT_CONTROLS)
        # Handling settings per player slot (1 = left board / human, 2 = right board / CPU or P2).
        self.handling: Dict[int, Dict[str, object]] = {
            1: dict(HANDLING_DEFAULTS), 2: dict(HANDLING_DEFAULTS)
        }

        self.state = App.STATE_TITLE
        self.running = True

        self.menu_options = ["40-Line Sprint", "Endless Mode", "Versus", "Settings", "Quit"]
        self.menu_index = 0

        self.versus_menu_options = ["Player vs Player", "Player vs CPU", "CPU vs CPU", "Back"]
        self.versus_menu_index = 0

        self.difficulty_menu_options: List[object] = DIFFICULTY_ORDER + ["Back"]
        self.difficulty_menu_index = 0
        self.pending_vs_mode: Optional[str] = None
        self._cpu1_difficulty: Optional[int] = None

        self.pause_options = ["Resume", "Restart", "Main Menu"]
        self.pause_index = 0
        self.gameover_index = 0

        self.controls_index = 0
        self.rebinding_action: Optional[str] = None

        # ---- Settings screen state ----
        self.settings_rows: List[Tuple[str, Optional[str]]] = (
            [("player", None)]
            + [("slider", s["key"]) for s in HANDLING_SLIDERS]
            + [("bool", b[0]) for b in HANDLING_BOOLS]
            + [("buffer", b[0]) for b in HANDLING_BUFFERS]
            + [("buttons", None)]
        )
        self.settings_buttons = ["Reset", "Test", "Controls", "Back"]
        self.settings_row = 0
        self.settings_player = 1
        self.settings_button = 1
        self.settings_hold_dir = 0
        self.settings_hold_timer = 0.0
        self.settings_hold_time = 0.0
        self.dragging_slider: Optional[str] = None

        # ---- Settings test state ----
        self.test_game: Optional[TetrisGame] = None
        self.test_fail_timer = 0.0

        self.current_mode = "sprint"
        self.game: Optional[TetrisGame] = None
        self.versus_match: Optional[VersusMatch] = None
        self.vs_opponent = "human"
        self.vs_difficulty: Optional[Union[int, Tuple[int, int]]] = None

    # -----------------------------------------------
    # Main loop
    # -----------------------------------------------
    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()

    def start_game(self, mode: str) -> None:
        self.current_mode = mode
        self.game = TetrisGame(mode, self.controls, handling=self.handling[1])
        self.state = App.STATE_PLAYING

    def start_versus(self, opponent: str,
                     difficulty: Optional[Union[int, Tuple[int, int]]] = None) -> None:
        self.vs_opponent = opponent
        self.vs_difficulty = difficulty
        self.versus_match = VersusMatch(self.controls, opponent, difficulty,
                                        handling_p1=self.handling[1],
                                        handling_p2=self.handling[2])
        self.state = App.STATE_PLAYING_VS

    def _resume_play(self, versus: bool = False) -> None:
        keys = pygame.key.get_pressed()
        if versus:
            self.versus_match.resync_held(keys)
            self.state = App.STATE_PLAYING_VS
        else:
            self.game.resync_held(keys)
            self.state = App.STATE_PLAYING

    # -----------------------------------------------
    # Events
    # -----------------------------------------------
    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if self.state == App.STATE_TITLE:
                if event.type == pygame.KEYDOWN:
                    self.state = App.STATE_MENU
            elif self.state == App.STATE_MENU:
                self._handle_menu_event(event)
            elif self.state == App.STATE_CONTROLS:
                self._handle_controls_event(event)
            elif self.state == App.STATE_SETTINGS:
                self._handle_settings_event(event)
            elif self.state == App.STATE_SETTINGS_TEST:
                self._handle_settings_test_event(event)
            elif self.state == App.STATE_VERSUS_MENU:
                self._handle_versus_menu_event(event)
            elif self.state == App.STATE_DIFFICULTY_MENU:
                self._handle_difficulty_menu_event(event)
            elif self.state == App.STATE_DIFFICULTY_MENU_2:
                self._handle_difficulty_menu2_event(event)
            elif self.state == App.STATE_PLAYING:
                if event.type == pygame.KEYDOWN and event.key == self.controls["pause"]:
                    self.state = App.STATE_PAUSED
                    self.pause_index = 0
                else:
                    self.game.handle_event(event)
            elif self.state == App.STATE_PAUSED:
                self._handle_pause_event(event)
            elif self.state == App.STATE_GAME_OVER:
                self._handle_game_over_event(event)
            elif self.state == App.STATE_PLAYING_VS:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.state = App.STATE_PAUSED_VS
                    self.pause_index = 0
                else:
                    self.versus_match.handle_event(event)
            elif self.state == App.STATE_PAUSED_VS:
                self._handle_pause_vs_event(event)
            elif self.state == App.STATE_VS_OVER:
                self._handle_vs_over_event(event)

    def _handle_menu_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_UP:
            self.menu_index = (self.menu_index - 1) % len(self.menu_options)
        elif event.key == pygame.K_DOWN:
            self.menu_index = (self.menu_index + 1) % len(self.menu_options)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            choice = self.menu_options[self.menu_index]
            if choice == "40-Line Sprint":
                self.start_game("sprint")
            elif choice == "Endless Mode":
                self.start_game("endless")
            elif choice == "Versus":
                self.state = App.STATE_VERSUS_MENU
                self.versus_menu_index = 0
            elif choice == "Settings":
                self.state = App.STATE_SETTINGS
                self.settings_row = 0
                self.settings_hold_dir = 0
            elif choice == "Quit":
                self.running = False

    def _handle_versus_menu_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_UP:
            self.versus_menu_index = (self.versus_menu_index - 1) % len(self.versus_menu_options)
        elif event.key == pygame.K_DOWN:
            self.versus_menu_index = (self.versus_menu_index + 1) % len(self.versus_menu_options)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            choice = self.versus_menu_options[self.versus_menu_index]
            if choice == "Player vs Player":
                self.start_versus("human")
            elif choice == "Player vs CPU":
                self.pending_vs_mode = "cpu"
                self.state = App.STATE_DIFFICULTY_MENU
                self.difficulty_menu_index = 0
            elif choice == "CPU vs CPU":
                self.pending_vs_mode = "cpu_vs_cpu"
                self.state = App.STATE_DIFFICULTY_MENU
                self.difficulty_menu_index = 0
            elif choice == "Back":
                self.state = App.STATE_MENU
        elif event.key == pygame.K_ESCAPE:
            self.state = App.STATE_MENU

    def _handle_difficulty_menu_event(self, event: pygame.event.Event) -> None:
        """First (or only) difficulty pick."""
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_UP:
            self.difficulty_menu_index = (self.difficulty_menu_index - 1) % len(self.difficulty_menu_options)
        elif event.key == pygame.K_DOWN:
            self.difficulty_menu_index = (self.difficulty_menu_index + 1) % len(self.difficulty_menu_options)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            choice = self.difficulty_menu_options[self.difficulty_menu_index]
            if choice == "Back":
                self.state = App.STATE_VERSUS_MENU
            elif self.pending_vs_mode == "cpu":
                self.start_versus("cpu", choice)
            else:  # "cpu_vs_cpu"
                self._cpu1_difficulty = choice
                self.difficulty_menu_index = 0
                self.state = App.STATE_DIFFICULTY_MENU_2
        elif event.key == pygame.K_ESCAPE:
            self.state = App.STATE_VERSUS_MENU

    def _handle_difficulty_menu2_event(self, event: pygame.event.Event) -> None:
        """Second difficulty pick, only used for 'cpu_vs_cpu' (CPU B's level)."""
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_UP:
            self.difficulty_menu_index = (self.difficulty_menu_index - 1) % len(self.difficulty_menu_options)
        elif event.key == pygame.K_DOWN:
            self.difficulty_menu_index = (self.difficulty_menu_index + 1) % len(self.difficulty_menu_options)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            choice = self.difficulty_menu_options[self.difficulty_menu_index]
            if choice == "Back":
                self.difficulty_menu_index = 0
                self.state = App.STATE_DIFFICULTY_MENU
            else:
                self.start_versus("cpu_vs_cpu", (self._cpu1_difficulty, choice))
        elif event.key == pygame.K_ESCAPE:
            self.difficulty_menu_index = 0
            self.state = App.STATE_DIFFICULTY_MENU

    def _handle_controls_event(self, event: pygame.event.Event) -> None:
        total_rows = len(ACTION_ORDER) + 1
        if self.rebinding_action is not None:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.rebinding_action = None
                else:
                    self.controls[self.rebinding_action] = event.key
                    self.rebinding_action = None
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_UP:
            self.controls_index = (self.controls_index - 1) % total_rows
        elif event.key == pygame.K_DOWN:
            self.controls_index = (self.controls_index + 1) % total_rows
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.controls_index == len(ACTION_ORDER):
                self.state = App.STATE_SETTINGS
            else:
                self.rebinding_action = ACTION_ORDER[self.controls_index]
        elif event.key == pygame.K_ESCAPE:
            self.state = App.STATE_SETTINGS

    # ---------- Settings screen ----------
    def _settings_row_y(self, i: int) -> int:
        return SET_ROW_Y0 + i * SET_ROW_GAP

    def _settings_adjust(self, direction: int, amount: int = 1) -> None:
        """direction: -1 = left (toward 'slow' / previous), +1 = right (toward 'fast' / next)."""
        kind, key = self.settings_rows[self.settings_row]
        h = self.handling[self.settings_player]
        if kind == "player":
            self.settings_player = 3 - self.settings_player
        elif kind == "slider":
            h[key] = slider_step(SLIDER_BY_KEY[key], h[key], direction * amount)
        elif kind == "bool":
            h[key] = not h[key]
        elif kind == "buffer":
            idx = BUFFER_MODES.index(h[key])
            h[key] = BUFFER_MODES[(idx + direction) % len(BUFFER_MODES)]
        elif kind == "buttons":
            self.settings_button = (self.settings_button + direction) % len(self.settings_buttons)

    def _settings_activate_button(self) -> None:
        name = self.settings_buttons[self.settings_button]
        if name == "Reset":
            self.handling[self.settings_player] = dict(HANDLING_DEFAULTS)
        elif name == "Test":
            self.start_settings_test()
        elif name == "Controls":
            self.state = App.STATE_CONTROLS
            self.controls_index = 0
            self.settings_hold_dir = 0
        elif name == "Back":
            self.state = App.STATE_MENU

    def _settings_slider_at(self, pos) -> Optional[Tuple[int, str]]:
        for i, (kind, key) in enumerate(self.settings_rows):
            if kind != "slider":
                continue
            y = self._settings_row_y(i)
            if pygame.Rect(SET_TRACK_X - 12, y - 4, SET_TRACK_W + 24, 32).collidepoint(pos):
                return i, key
        return None

    def _set_slider_from_x(self, key: str, x: int) -> None:
        spec = SLIDER_BY_KEY[key]
        f = max(0.0, min(1.0, (x - SET_TRACK_X) / float(SET_TRACK_W)))
        self.handling[self.settings_player][key] = slider_value_from_fraction(spec, f)

    def _handle_settings_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYUP:
            if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                self.settings_hold_dir = 0
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hit = self._settings_slider_at(event.pos)
            if hit is not None:
                self.settings_row, key = hit
                self.dragging_slider = key
                self._set_slider_from_x(key, event.pos[0])
            return
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_slider = None
            return
        if event.type == pygame.MOUSEMOTION and self.dragging_slider is not None:
            self._set_slider_from_x(self.dragging_slider, event.pos[0])
            return

        if event.type != pygame.KEYDOWN:
            return
        total = len(self.settings_rows)
        kind, _ = self.settings_rows[self.settings_row]
        if event.key == pygame.K_UP:
            self.settings_row = (self.settings_row - 1) % total
            self.settings_hold_dir = 0
        elif event.key == pygame.K_DOWN:
            self.settings_row = (self.settings_row + 1) % total
            self.settings_hold_dir = 0
        elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            d = -1 if event.key == pygame.K_LEFT else 1
            self._settings_adjust(d)
            if kind == "slider":
                self.settings_hold_dir = d
                self.settings_hold_timer = 0.4
                self.settings_hold_time = 0.0
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if kind == "buttons":
                self._settings_activate_button()
            else:
                self._settings_adjust(1)
        elif event.key == pygame.K_ESCAPE:
            self.state = App.STATE_MENU

    def _update_settings(self, dt: float) -> None:
        """Hold Left/Right on a slider to keep adjusting it (accelerates the longer it's held)."""
        kind, _ = self.settings_rows[self.settings_row]
        if self.settings_hold_dir == 0 or kind != "slider":
            return
        self.settings_hold_time += dt
        self.settings_hold_timer -= dt
        while self.settings_hold_timer <= 0:
            amount = 1
            if self.settings_hold_time > 1.6:
                amount = 5
            elif self.settings_hold_time > 0.9:
                amount = 2
            self._settings_adjust(self.settings_hold_dir, amount)
            self.settings_hold_timer += 0.03

    # ---------- Settings test ----------
    def start_settings_test(self) -> None:
        self.settings_hold_dir = 0
        self._new_test_game()
        self.state = App.STATE_SETTINGS_TEST

    def _new_test_game(self) -> None:
        p = self.settings_player
        controls = self.controls if p == 1 else DEFAULT_CONTROLS_P2
        self.test_game = TetrisGame("test", controls, handling=self.handling[p])
        self.test_game.resync_held(pygame.key.get_pressed())
        self.test_fail_timer = 0.0

    def _handle_settings_test_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.test_game = None
            self.state = App.STATE_SETTINGS
            return
        self.test_game.handle_event(event)

    # ---------- Pause / game over ----------
    def _handle_pause_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == self.controls["pause"]:
            self._resume_play()
            return
        if event.key == pygame.K_UP:
            self.pause_index = (self.pause_index - 1) % len(self.pause_options)
        elif event.key == pygame.K_DOWN:
            self.pause_index = (self.pause_index + 1) % len(self.pause_options)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            choice = self.pause_options[self.pause_index]
            if choice == "Resume":
                self._resume_play()
            elif choice == "Restart":
                self.start_game(self.current_mode)
            elif choice == "Main Menu":
                self.game = None
                self.state = App.STATE_MENU

    def _handle_pause_vs_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self._resume_play(versus=True)
            return
        if event.key == pygame.K_UP:
            self.pause_index = (self.pause_index - 1) % len(self.pause_options)
        elif event.key == pygame.K_DOWN:
            self.pause_index = (self.pause_index + 1) % len(self.pause_options)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            choice = self.pause_options[self.pause_index]
            if choice == "Resume":
                self._resume_play(versus=True)
            elif choice == "Restart":
                self.start_versus(self.vs_opponent, self.vs_difficulty)
            elif choice == "Main Menu":
                self.versus_match = None
                self.state = App.STATE_MENU

    def _handle_game_over_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.gameover_index = 1 - self.gameover_index
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.gameover_index == 0:
                self.start_game(self.current_mode)
            else:
                self.game = None
                self.state = App.STATE_MENU
        elif event.key == pygame.K_ESCAPE:
            self.game = None
            self.state = App.STATE_MENU

    def _handle_vs_over_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.start_versus(self.vs_opponent, self.vs_difficulty)
        elif event.key == pygame.K_ESCAPE:
            self.versus_match = None
            self.state = App.STATE_MENU

    # -----------------------------------------------
    # Update (frame-rate independent)
    # -----------------------------------------------
    def update(self, dt: float) -> None:
        dt = min(dt, MAX_FRAME_TIME)
        if self.state == App.STATE_SETTINGS:
            self._update_settings(dt)
            return
        if self.state not in (App.STATE_PLAYING, App.STATE_PLAYING_VS, App.STATE_SETTINGS_TEST):
            return

        # Advance the simulation in small fixed-size slices so gameplay is
        # identical whether we render at 20 FPS or 240 FPS.
        keys = pygame.key.get_pressed()
        start_state = self.state
        remaining = dt
        while remaining > 1e-9 and self.state == start_state:
            step = min(remaining, MAX_SIM_STEP)
            remaining -= step
            self._sim_step(step, keys)

    def _sim_step(self, dt: float, keys) -> None:
        if self.state == App.STATE_PLAYING and self.game is not None:
            self.game.update(dt, keys)
            if self.game.game_over:
                self.gameover_index = 0
                self.state = App.STATE_GAME_OVER
        elif self.state == App.STATE_PLAYING_VS and self.versus_match is not None:
            self.versus_match.update(dt, keys)
            if self.versus_match.finished:
                self.state = App.STATE_VS_OVER
        elif self.state == App.STATE_SETTINGS_TEST and self.test_game is not None:
            if self.test_game.game_over:
                # Topped out: show the failure for a moment, then reset automatically.
                self.test_fail_timer += dt
                if self.test_fail_timer >= TEST_FAIL_DELAY:
                    self._new_test_game()
            else:
                self.test_game.update(dt, keys)

    # -----------------------------------------------
    # Draw
    # -----------------------------------------------
    def draw(self) -> None:
        if self.state == App.STATE_TITLE:
            self._draw_title()
        elif self.state == App.STATE_MENU:
            self._draw_menu()
        elif self.state == App.STATE_CONTROLS:
            self._draw_controls()
        elif self.state == App.STATE_SETTINGS:
            self._draw_settings()
        elif self.state == App.STATE_SETTINGS_TEST:
            self._draw_settings_test()
        elif self.state == App.STATE_VERSUS_MENU:
            self._draw_versus_menu()
        elif self.state == App.STATE_DIFFICULTY_MENU:
            title = "SELECT CPU DIFFICULTY" if self.pending_vs_mode == "cpu" else "SELECT DIFFICULTY - CPU A"
            self._draw_difficulty_menu(title)
        elif self.state == App.STATE_DIFFICULTY_MENU_2:
            self._draw_difficulty_menu("SELECT DIFFICULTY - CPU B")
        elif self.state == App.STATE_PLAYING:
            self.screen.fill(BLACK)
            self.game.draw(self.screen, self.font_small, self.font_med)
        elif self.state == App.STATE_PAUSED:
            self.screen.fill(BLACK)
            self.game.draw(self.screen, self.font_small, self.font_med)
            self._draw_pause_overlay()
        elif self.state == App.STATE_GAME_OVER:
            self._draw_game_over()
        elif self.state == App.STATE_PLAYING_VS:
            self.versus_match.draw(self.screen, self.font_small, self.font_med, self.font_big)
        elif self.state == App.STATE_PAUSED_VS:
            self.versus_match.draw(self.screen, self.font_small, self.font_med, self.font_big)
            self._draw_pause_overlay()
        elif self.state == App.STATE_VS_OVER:
            self.versus_match.draw(self.screen, self.font_small, self.font_med, self.font_big)
        pygame.display.flip()

    @staticmethod
    def _wrap_text(text: str, font: pygame.font.Font, max_w: int) -> List[str]:
        lines: List[str] = []
        cur = ""
        for word in text.split():
            trial = (cur + " " + word).strip()
            if font.size(trial)[0] <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def _draw_title(self) -> None:
        self.screen.fill(BLACK)
        title_surf = self.font_title.render("TETRIS", True, CYAN)
        self.screen.blit(title_surf, ((WINDOW_WIDTH - title_surf.get_width()) // 2, 220))
        prompt_surf = self.font_med.render("Press any key to continue", True, WHITE)
        self.screen.blit(prompt_surf, ((WINDOW_WIDTH - prompt_surf.get_width()) // 2, 340))
        hint_surf = self.font_small.render(
            "40-Line Sprint  |  Endless Mode  |  Versus (PvP, vs CPU, or CPU vs CPU)  |  Controls & Handling",
            True, GRAY)
        self.screen.blit(hint_surf, ((WINDOW_WIDTH - hint_surf.get_width()) // 2, 400))

    def _draw_menu(self) -> None:
        self.screen.fill(BLACK)
        title_surf = self.font_big.render("MAIN MENU", True, WHITE)
        self.screen.blit(title_surf, ((WINDOW_WIDTH - title_surf.get_width()) // 2, 90))
        start_y = 190
        gap = 55
        for i, option in enumerate(self.menu_options):
            color = YELLOW if i == self.menu_index else WHITE
            text_surf = self.font_med.render(option, True, color)
            x = (WINDOW_WIDTH - text_surf.get_width()) // 2
            y = start_y + i * gap
            if i == self.menu_index:
                marker = self.font_med.render(">", True, YELLOW)
                self.screen.blit(marker, (x - 40, y))
            self.screen.blit(text_surf, (x, y))
        hint_surf = self.font_small.render("Arrow keys to navigate, Enter to select", True, GRAY)
        self.screen.blit(hint_surf, ((WINDOW_WIDTH - hint_surf.get_width()) // 2, 620))

    def _draw_versus_menu(self) -> None:
        self.screen.fill(BLACK)
        title_surf = self.font_big.render("VERSUS", True, WHITE)
        self.screen.blit(title_surf, ((WINDOW_WIDTH - title_surf.get_width()) // 2, 130))
        start_y = 250
        gap = 55
        for i, option in enumerate(self.versus_menu_options):
            color = YELLOW if i == self.versus_menu_index else WHITE
            text_surf = self.font_med.render(option, True, color)
            x = (WINDOW_WIDTH - text_surf.get_width()) // 2
            y = start_y + i * gap
            if i == self.versus_menu_index:
                marker = self.font_med.render(">", True, YELLOW)
                self.screen.blit(marker, (x - 40, y))
            self.screen.blit(text_surf, (x, y))
        hint_surf = self.font_small.render(
            "Player 1: your configured controls   |   Player 2: WASD, Q/E rotate, Shift hold",
            True, GRAY)
        self.screen.blit(hint_surf, ((WINDOW_WIDTH - hint_surf.get_width()) // 2, 500))
        hint2_surf = self.font_small.render(
            "CPUs use the Handling settings of their player slot (P1 = left board, P2 = right board). Esc to go back",
            True, GRAY)
        self.screen.blit(hint2_surf, ((WINDOW_WIDTH - hint2_surf.get_width()) // 2, 600))

    def _draw_difficulty_menu(self, title: str) -> None:
        self.screen.fill(BLACK)
        title_surf = self.font_big.render(title, True, WHITE)
        self.screen.blit(title_surf, ((WINDOW_WIDTH - title_surf.get_width()) // 2, 60))
        start_y = 140
        gap = 46
        for i, option in enumerate(self.difficulty_menu_options):
            label = "Back" if option == "Back" else difficulty_label(option)
            color = YELLOW if i == self.difficulty_menu_index else WHITE
            text_surf = self.font_med.render(label, True, color)
            x = (WINDOW_WIDTH - text_surf.get_width()) // 2
            y = start_y + i * gap
            if i == self.difficulty_menu_index:
                marker = self.font_med.render(">", True, YELLOW)
                self.screen.blit(marker, (x - 40, y))
            self.screen.blit(text_surf, (x, y))
            if option != "Back":
                desc = difficulty_description(option)
                desc_surf = self.font_tiny.render(desc, True, GRAY)
                self.screen.blit(desc_surf, ((WINDOW_WIDTH - desc_surf.get_width()) // 2, y + 24))
        hint_surf = self.font_small.render("Esc to go back", True, GRAY)
        self.screen.blit(hint_surf, ((WINDOW_WIDTH - hint_surf.get_width()) // 2, 662))

    def _draw_controls(self) -> None:
        self.screen.fill(BLACK)
        title_surf = self.font_big.render("CONTROLS (Player 1)", True, WHITE)
        self.screen.blit(title_surf, ((WINDOW_WIDTH - title_surf.get_width()) // 2, 40))
        start_y = 130
        gap = 42
        for i, action in enumerate(ACTION_ORDER):
            label = ACTION_LABELS[action]
            key_name = pygame.key.name(self.controls[action]).upper()
            is_selected = (i == self.controls_index)
            is_rebinding = (self.rebinding_action == action)
            color = YELLOW if is_selected else WHITE
            label_surf = self.font_med.render(label, True, color)
            self.screen.blit(label_surf, (WINDOW_WIDTH // 2 - 250, start_y + i * gap))
            key_str = "Press any key..." if is_rebinding else key_name
            key_color = CYAN if is_rebinding else color
            key_surf = self.font_med.render(key_str, True, key_color)
            self.screen.blit(key_surf, (WINDOW_WIDTH // 2 + 80, start_y + i * gap))
        back_index = len(ACTION_ORDER)
        back_color = YELLOW if self.controls_index == back_index else WHITE
        back_surf = self.font_med.render("Back", True, back_color)
        self.screen.blit(back_surf, ((WINDOW_WIDTH - back_surf.get_width()) // 2,
                                     start_y + back_index * gap + 20))
        hint_surf = self.font_small.render(
            "Enter to rebind a control, Esc to cancel a rebind or go back", True, GRAY)
        self.screen.blit(hint_surf, ((WINDOW_WIDTH - hint_surf.get_width()) // 2, 590))
        p2_surf = self.font_small.render(
            "Player 2 (versus, fixed): A/D move, S soft drop, W hard drop, Q/E rotate, Shift hold",
            True, GRAY)
        self.screen.blit(p2_surf, ((WINDOW_WIDTH - p2_surf.get_width()) // 2, 625))

    # ---------- Settings drawing ----------
    def _draw_settings(self) -> None:
        s = self.screen
        s.fill(BLACK)
        title = self.font_big.render("SETTINGS - HANDLING", True, WHITE)
        s.blit(title, ((WINDOW_WIDTH - title.get_width()) // 2, 16))

        p = self.settings_player
        h = self.handling[p]
        for i, (kind, key) in enumerate(self.settings_rows):
            y = self._settings_row_y(i)
            selected = (i == self.settings_row)
            color = YELLOW if selected else WHITE
            if selected and kind != "buttons":
                s.blit(self.font_small.render(">", True, YELLOW), (SET_LABEL_X - 24, y))

            if kind == "player":
                s.blit(self.font_small.render("Player", True, color), (SET_LABEL_X, y))
                pc = CYAN if p == 1 else ORANGE
                txt = self.font_small.render(f"<   Player {p}   >", True, pc)
                s.blit(txt, (SET_TRACK_X, y))
                note = self.font_tiny.render("(CPUs use the settings of their player slot)", True, GRAY)
                s.blit(note, (SET_TRACK_X + 170, y + 3))

            elif kind == "slider":
                spec = SLIDER_BY_KEY[key]
                v = h[key]
                s.blit(self.font_small.render(spec["label"], True, color), (SET_LABEL_X, y))
                s.blit(self.font_tiny.render("SLOW", True, GRAY), (SET_TRACK_X - 46, y + 4))
                s.blit(self.font_tiny.render("FAST", True, GRAY), (SET_TRACK_X + SET_TRACK_W + 12, y + 4))
                track = pygame.Rect(SET_TRACK_X, y + 9, SET_TRACK_W, 6)
                pygame.draw.rect(s, (60, 60, 60), track, border_radius=3)
                knob_x = SET_TRACK_X + int(slider_fraction(spec, v) * SET_TRACK_W)
                fill = pygame.Rect(SET_TRACK_X, y + 9, knob_x - SET_TRACK_X, 6)
                if fill.width > 0:
                    pygame.draw.rect(s, CYAN if selected else GRAY, fill, border_radius=3)
                pygame.draw.circle(s, YELLOW if selected else WHITE, (knob_x, y + 12), 9)
                val = self.font_small.render(format_slider_value(spec, v), True, color)
                s.blit(val, (SET_TRACK_X + SET_TRACK_W + 70, y))

            elif kind == "bool":
                _, label, _desc = BOOL_BY_KEY[key]
                s.blit(self.font_small.render(label, True, color), (SET_LABEL_X, y))
                on = bool(h[key])
                s.blit(self.font_small.render("ON" if on else "OFF", True, GREEN if on else RED),
                       (SET_TRACK_X, y))

            elif kind == "buffer":
                _, label, _descs = BUFFER_BY_KEY[key]
                s.blit(self.font_small.render(label, True, color), (SET_LABEL_X, y))
                for j, mode in enumerate(BUFFER_MODES):
                    is_cur = (h[key] == mode)
                    name = BUFFER_MODE_LABELS[mode]
                    if is_cur:
                        txt = self.font_small.render(f"[ {name} ]", True, YELLOW if selected else WHITE)
                    else:
                        txt = self.font_small.render(name, True, GRAY)
                    s.blit(txt, (SET_TRACK_X + j * 100, y))

            elif kind == "buttons":
                total_w = len(self.settings_buttons) * 130 + (len(self.settings_buttons) - 1) * 20
                start_x = (WINDOW_WIDTH - total_w) // 2
                for j, name in enumerate(self.settings_buttons):
                    rect = pygame.Rect(start_x + j * 150, y - 2, 130, 34)
                    is_sel = selected and j == self.settings_button
                    if is_sel:
                        pygame.draw.rect(s, YELLOW, rect, border_radius=6)
                    else:
                        pygame.draw.rect(s, GRAY, rect, 2, border_radius=6)
                    t = self.font_small.render(name, True, BLACK if is_sel else WHITE)
                    s.blit(t, (rect.x + (rect.width - t.get_width()) // 2,
                               rect.y + (rect.height - t.get_height()) // 2))

        # ---- Description box for the selected row ----
        box = pygame.Rect(40, 510, WINDOW_WIDTH - 80, 150)
        pygame.draw.rect(s, (25, 25, 25), box, border_radius=6)
        pygame.draw.rect(s, GRAY, box, 1, border_radius=6)
        kind, key = self.settings_rows[self.settings_row]
        tx, ty, max_w = box.x + 16, box.y + 12, box.width - 32

        def draw_block(text: str, color, y0: int) -> int:
            for line in self._wrap_text(text, self.font_small, max_w):
                s.blit(self.font_small.render(line, True, color), (tx, y0))
                y0 += 24
            return y0

        if kind == "player":
            draw_block("Player 1 settings are used by the human player (or CPU A). Player 2 "
                       "settings are used by Player 2 or the CPU opponent. Left/Right to switch.",
                       WHITE, ty)
        elif kind == "slider":
            spec = SLIDER_BY_KEY[key]
            draw_block(spec["desc"], WHITE, ty)
            default = format_slider_value(spec, HANDLING_DEFAULTS[key])
            lo, hi = slider_min_max(spec)
            rng = f"Range: {format_slider_value(spec, spec['slow'])} (slow) to " \
                  f"{format_slider_value(spec, spec['fast'])} (fast)   |   Default: {default}"
            s.blit(self.font_tiny.render(rng, True, GRAY), (tx, box.bottom - 28))
        elif kind == "bool":
            draw_block(BOOL_BY_KEY[key][2], WHITE, ty)
            default = "ON" if HANDLING_DEFAULTS[key] else "OFF"
            s.blit(self.font_tiny.render(f"Default: {default}", True, GRAY), (tx, box.bottom - 28))
        elif kind == "buffer":
            descs = BUFFER_BY_KEY[key][2]
            yy = ty
            for mode in BUFFER_MODES:
                cur = (h[key] == mode)
                text = f"{BUFFER_MODE_LABELS[mode]}: {descs[mode]}"
                yy = draw_block(text, YELLOW if cur else GRAY, yy)
            default = BUFFER_MODE_LABELS[HANDLING_DEFAULTS[key]]
            s.blit(self.font_tiny.render(f"Default: {default}", True, GRAY), (tx, box.bottom - 24))
        elif kind == "buttons":
            name = self.settings_buttons[self.settings_button]
            msg = {
                "Reset": f"Restore all Player {p} handling settings to their defaults.",
                "Test": f"Try Player {p}'s settings in an endless practice game. If you top out it "
                        f"resets automatically. Press Esc to return here with your settings intact.",
                "Controls": "Rebind Player 1's keys. Esc or Back returns to Settings.",
                "Back": "Return to the main menu. Settings are kept.",
            }[name]
            draw_block(msg, WHITE, ty)

        hint = self.font_tiny.render(
            "Up/Down: select    Left/Right: adjust (hold to speed up)    Enter: toggle / press button    "
            "Mouse: drag sliders    Esc: back", True, GRAY)
        s.blit(hint, ((WINDOW_WIDTH - hint.get_width()) // 2, 672))

    def _draw_settings_test(self) -> None:
        s = self.screen
        s.fill(BLACK)
        g = self.test_game
        g.draw(s, self.font_small, self.font_med)

        p = self.settings_player
        h = self.handling[p]
        x, y = 20, 330
        pc = CYAN if p == 1 else ORANGE
        s.blit(self.font_med.render(f"TEST - Player {p}", True, pc), (x, y))
        y += 34
        for spec in HANDLING_SLIDERS:
            line = f"{spec['label']}: {format_slider_value(spec, h[spec['key']])}"
            s.blit(self.font_tiny.render(line, True, GRAY), (x, y))
            y += 20
        for key, label in (("irs", "IRS"), ("ihs", "IHS")):
            s.blit(self.font_tiny.render(f"{label}: {BUFFER_MODE_LABELS[h[key]]}", True, GRAY), (x, y))
            y += 20
        y += 14
        s.blit(self.font_small.render("Esc: back to settings", True, WHITE), (x, y))

        if g.game_over:
            overlay = pygame.Surface((GRID_WIDTH * BLOCK_SIZE, GRID_HEIGHT * BLOCK_SIZE), pygame.SRCALPHA)
            overlay.fill((120, 0, 0, 150))
            s.blit(overlay, (BOARD_X, BOARD_Y))
            txt = self.font_big.render("TOPPED OUT", True, WHITE)
            s.blit(txt, (BOARD_X + (GRID_WIDTH * BLOCK_SIZE - txt.get_width()) // 2,
                         BOARD_Y + GRID_HEIGHT * BLOCK_SIZE // 2 - 20))

    def _draw_pause_overlay(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        title_surf = self.font_big.render("PAUSED", True, WHITE)
        self.screen.blit(title_surf, ((WINDOW_WIDTH - title_surf.get_width()) // 2, 220))
        start_y = 320
        gap = 50
        for i, option in enumerate(self.pause_options):
            color = YELLOW if i == self.pause_index else WHITE
            text_surf = self.font_med.render(option, True, color)
            x = (WINDOW_WIDTH - text_surf.get_width()) // 2
            y = start_y + i * gap
            if i == self.pause_index:
                marker = self.font_med.render(">", True, YELLOW)
                self.screen.blit(marker, (x - 40, y))
            self.screen.blit(text_surf, (x, y))

    def _draw_game_over(self) -> None:
        self.screen.fill(BLACK)
        g = self.game
        minutes = int(g.total_time // 60)
        seconds = int(g.total_time % 60)
        header = "40 LINES CLEARED!" if g.cleared else "GAME OVER"
        header_surf = self.font_title.render(header, True, WHITE if not g.cleared else YELLOW)
        if header_surf.get_width() > WINDOW_WIDTH - 40:
            header_surf = self.font_big.render(header, True, WHITE if not g.cleared else YELLOW)
        self.screen.blit(header_surf, ((WINDOW_WIDTH - header_surf.get_width()) // 2, 110))

        if g.line_target is not None:
            lines_str = f"Lines cleared: {min(g.lines_cleared, g.line_target)}/{g.line_target}"
        else:
            lines_str = f"Lines cleared: {g.lines_cleared}"
        lines_surf = self.font_med.render(lines_str, True, WHITE)
        self.screen.blit(lines_surf, ((WINDOW_WIDTH - lines_surf.get_width()) // 2, 200))

        time_surf = self.font_med.render(f"Time: {minutes}:{seconds:02d}", True, WHITE)
        self.screen.blit(time_surf, ((WINDOW_WIDTH - time_surf.get_width()) // 2, 240))

        prompt_surf = self.font_med.render("Play again?", True, WHITE)
        self.screen.blit(prompt_surf, ((WINDOW_WIDTH - prompt_surf.get_width()) // 2, 320))

        yes_text = self.font_med.render("Yes", True, BLACK)
        no_text = self.font_med.render("No", True, BLACK)
        yes_rect = pygame.Rect(WINDOW_WIDTH // 2 - 110, 380, 90, 44)
        no_rect = pygame.Rect(WINDOW_WIDTH // 2 + 20, 380, 90, 44)
        if self.gameover_index == 0:
            pygame.draw.rect(self.screen, YELLOW, yes_rect)
            pygame.draw.rect(self.screen, GRAY, no_rect)
        else:
            pygame.draw.rect(self.screen, GRAY, yes_rect)
            pygame.draw.rect(self.screen, YELLOW, no_rect)
        self.screen.blit(yes_text, (yes_rect.x + (yes_rect.width - yes_text.get_width()) // 2,
                                    yes_rect.y + (yes_rect.height - yes_text.get_height()) // 2))
        self.screen.blit(no_text, (no_rect.x + (no_rect.width - no_text.get_width()) // 2,
                                   no_rect.y + (no_rect.height - no_text.get_height()) // 2))

        hint_surf = self.font_small.render(
            "\"Yes\" plays again  |  \"No\" returns to the Main Menu", True, GRAY)
        self.screen.blit(hint_surf, ((WINDOW_WIDTH - hint_surf.get_width()) // 2, 450))
        hint2_surf = self.font_small.render(
            "Left/Right to choose, Enter to confirm", True, GRAY)
        self.screen.blit(hint2_surf, ((WINDOW_WIDTH - hint2_surf.get_width()) // 2, 480))


def main():
    app = App()
    app.run()


if __name__ == "__main__":
    main()