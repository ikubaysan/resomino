import pygame
import sys
import random
from typing import List, Tuple, Optional, Dict

pygame.init()

# ---------------------------------------------------
# Window and Board Settings
# ---------------------------------------------------
WINDOW_WIDTH = 780
WINDOW_HEIGHT = 700
GRID_WIDTH = 10   # Tetris: 10 columns
GRID_HEIGHT = 20  # Tetris: 20 rows
BLOCK_SIZE = 30   # Each cell is 30x30 pixels

# We'll place the board at (BOARD_X, BOARD_Y)
BOARD_X = (WINDOW_WIDTH - GRID_WIDTH * BLOCK_SIZE) // 2
BOARD_Y = 60  # Some margin from the top

# Offsets for the "Hold" area and "Next" area
HOLD_AREA_X = 20
HOLD_AREA_Y = 80
NEXT_AREA_X = WINDOW_WIDTH - 150
NEXT_AREA_Y = 80
NUM_NEXT_PIECES = 6  # was 2 -- now shows 4 more (6 total)

FPS = 60
LOCK_DELAY = 0.5  # 0.5 seconds of "floor time" before piece locks
MAX_LOCK_RESETS = 15  # classic-Tetris-style cap: after this many resets while
                       # grounded, the piece is no longer allowed to postpone
                       # locking indefinitely by moving/rotating.

# Key repeat settings (in seconds) for movement (handled manually, NOT via
# pygame.key.set_repeat, so that rotate/hold presses never get spammed by
# the OS-level key-repeat system).
MOVE_REPEAT_INITIAL_DELAY = 0.2  # How long to hold before repeat starts
MOVE_REPEAT_INTERVAL = 0.05      # How quickly repeated moves happen

# ---------------------------------------------------
# Tetromino Definitions
# ---------------------------------------------------
TETROMINOES = {
    "I": [
        [(0, 0), (1, 0), (2, 0), (3, 0)],
        [(0, 0), (0, 1), (0, 2), (0, 3)],
        [(0, 0), (1, 0), (2, 0), (3, 0)],
        [(0, 0), (0, 1), (0, 2), (0, 3)],
    ],
    "O": [
        [(0, 0), (1, 0), (0, 1), (1, 1)],
        [(0, 0), (1, 0), (0, 1), (1, 1)],
        [(0, 0), (1, 0), (0, 1), (1, 1)],
        [(0, 0), (1, 0), (0, 1), (1, 1)],
    ],
    "T": [
        [(0, 1), (1, 1), (2, 1), (1, 0)],
        [(1, 0), (1, 1), (1, 2), (2, 1)],
        [(0, 0), (1, 0), (2, 0), (1, 1)],
        [(0, 1), (1, 1), (1, 0), (1, 2)],
    ],
    "S": [
        [(1, 0), (2, 0), (0, 1), (1, 1)],
        [(1, 0), (1, 1), (2, 1), (2, 2)],
        [(1, 1), (2, 1), (0, 2), (1, 2)],
        [(0, 0), (0, 1), (1, 1), (1, 2)],
    ],
    "Z": [
        [(0, 0), (1, 0), (1, 1), (2, 1)],
        [(1, -1), (1, 0), (0, 0), (0, 1)],
        [(0, 0), (1, 0), (1, 1), (2, 1)],
        [(1, -1), (1, 0), (0, 0), (0, 1)],
    ],
    "L": [
        [(0, 0), (0, 1), (0, 2), (1, 2)],
        [(0, 0), (1, 0), (2, 0), (0, 1)],
        [(1, 0), (1, 1), (1, 2), (0, 0)],
        [(0, 1), (1, 1), (2, 1), (2, 0)],
    ],
    "J": [
        [(1, 0), (1, 1), (1, 2), (0, 2)],
        [(0, 0), (0, 1), (1, 1), (2, 1)],
        [(0, 0), (0, 1), (0, 2), (1, 0)],
        [(0, 0), (1, 0), (2, 0), (2, 1)],
    ],
}

COLORS: Dict[str, Tuple[int, int, int]] = {
    "I": (0, 255, 255),     # Cyan
    "O": (255, 255, 0),     # Yellow
    "T": (128, 0, 128),     # Purple
    "S": (0, 255, 0),       # Green
    "Z": (255, 0, 0),       # Red
    "J": (0, 0, 255),       # Blue
    "L": (255, 165, 0),     # Orange
}

# Ghost piece color (gray).
GHOST_COLOR = (100, 100, 100)

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

ACTION_ORDER = [
    "left", "right", "soft_drop", "hard_drop",
    "rotate_cw", "rotate_ccw", "hold", "pause",
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

def _generate_wall_kicks() -> List[Tuple[int, int]]:
    """
    Build the list of (dx, dy) offsets to try, in order of preference, when
    a rotation doesn't fit in place: smallest shift first; among equal-sized
    shifts, pure horizontal, then pure vertical, then diagonal; negative
    before positive.

    Magnitude 3 is required in BOTH axes for the I piece: its "vertical"
    form is only 1 column wide but 4 rows tall, so rotating it back to
    horizontal (4 columns, 1 row) next to a side wall can need up to a
    3-column shift, and rotating it into vertical near the floor/top can
    need up to a 3-row shift.
    """
    kicks: List[Tuple[int, int]] = []
    for mag in (1, 2, 3):
        candidates = []
        for dx in range(-mag, mag + 1):
            for dy in range(-mag, mag + 1):
                if max(abs(dx), abs(dy)) != mag:
                    continue
                candidates.append((dx, dy))

        def sort_key(t):
            dx, dy = t
            category = 0 if dy == 0 else (1 if dx == 0 else 2)  # horiz, vert, diagonal
            return (category, 0 if dx < 0 else 1, 0 if dy < 0 else 1)

        candidates.sort(key=sort_key)
        kicks.extend(candidates)
    return kicks


# Colors used throughout the UI
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
DARK_GRAY = (40, 40, 40)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)


class Tetromino:
    def __init__(self, shape: str):
        self.shape: str = shape
        self.rotation_index: int = 0
        self.x: int = 3  # Column 3 (somewhere near the middle)
        self.y: int = 0
        self.color: Tuple[int, int, int] = COLORS[shape]

    def get_blocks(self) -> List[Tuple[int, int]]:
        """
        Return the list of (x, y) block positions for the current rotation
        of this Tetromino.
        """
        rotation_variants = TETROMINOES[self.shape]
        coords = rotation_variants[self.rotation_index % len(rotation_variants)]
        return [(self.x + cx, self.y + cy) for (cx, cy) in coords]

    def rotate(self, direction: int) -> None:
        """
        Rotate the piece in the given direction (1 for clockwise, -1 for
        counter-clockwise).
        """
        self.rotation_index = (self.rotation_index + direction) % len(TETROMINOES[self.shape])


class TetrisGame:
    """
    Holds all logic/state for a single round of Tetris. Has no event loop of
    its own -- the App class drives it by calling handle_event()/update()/
    draw() each frame, which also makes pausing trivial (simply stop calling
    update()).
    """

    def __init__(self, mode: str, controls: Dict[str, int]) -> None:
        self.mode = mode  # "sprint" (40-line time attack) or "endless"
        self.line_target: Optional[int] = 40 if mode == "sprint" else None
        self.controls = controls

        # Board 2D array: None means empty cell, otherwise store a color
        self.board: List[List[Optional[Tuple[int, int, int]]]] = [
            [None] * GRID_WIDTH for _ in range(GRID_HEIGHT)
        ]

        self.lines_cleared = 0
        self.total_time = 0.0

        # Upcoming pieces (7-bag)
        self.upcoming_pieces: List[Tetromino] = []
        self._generate_new_bag()
        self._generate_new_bag()

        # Hold piece
        self.held_piece: Optional[Tetromino] = None
        self.hold_used_this_turn: bool = False

        # Current piece
        self.current_piece: Tetromino = self.upcoming_pieces.pop(0)

        # Drop timers
        self.drop_timer: float = 0.0
        self.drop_interval: float = 0.5  # seconds per auto-drop

        # Lock delay timers / anti-infinite-stall bookkeeping
        self.lock_timer: float = 0.0
        self.lock_resets: int = 0

        # Result flags -- App checks these each frame instead of TetrisGame
        # owning its own loop.
        self.game_over: bool = False
        self.cleared: bool = False  # True if a line-target (sprint) was met

        # Held-key tracking for manual repeat (left/right/soft-drop only --
        # rotation/hold/hard-drop are deliberately single-fire per press).
        self.hard_drop_held = False
        self.left_held = False
        self.right_held = False
        self.down_held = False
        self.h_move_cooldown = 0.0
        self.v_move_cooldown = 0.0
        self.initial_delay = MOVE_REPEAT_INITIAL_DELAY
        self.repeat_interval = MOVE_REPEAT_INTERVAL

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
        if self.game_over:
            return
        c = self.controls
        if event.type == pygame.KEYDOWN:
            if event.key == c["rotate_ccw"]:
                self.rotate_piece(-1)
            elif event.key == c["rotate_cw"]:
                self.rotate_piece(1)
            elif event.key == c["hard_drop"] and not self.hard_drop_held:
                self.hard_drop()
                self.hard_drop_held = True
            elif event.key == c["hold"]:
                self.hold_piece()
            elif event.key == c["left"]:
                self.left_held = True
                self.move_piece(dx=-1)
                self.h_move_cooldown = self.initial_delay
            elif event.key == c["right"]:
                self.right_held = True
                self.move_piece(dx=1)
                self.h_move_cooldown = self.initial_delay
            elif event.key == c["soft_drop"]:
                self.down_held = True
                self.soft_drop()
                self.v_move_cooldown = self.initial_delay
        elif event.type == pygame.KEYUP:
            if event.key == c["hard_drop"]:
                self.hard_drop_held = False
            elif event.key == c["left"]:
                self.left_held = False
            elif event.key == c["right"]:
                self.right_held = False
            elif event.key == c["soft_drop"]:
                self.down_held = False

    # -----------------------------------------------
    # Update
    # -----------------------------------------------
    def update(self, dt: float, keys) -> None:
        if self.game_over:
            return
        c = self.controls

        # Manual repeat for movement -- rotation/hold/hard-drop are NOT
        # handled here, so holding them down can never spam extra presses.
        if self.left_held or self.right_held:
            self.h_move_cooldown -= dt
            if self.h_move_cooldown <= 0:
                if self.left_held and keys[c["left"]]:
                    self.move_piece(dx=-1)
                elif self.right_held and keys[c["right"]]:
                    self.move_piece(dx=1)
                self.h_move_cooldown = self.repeat_interval

        if self.down_held:
            self.v_move_cooldown -= dt
            if self.v_move_cooldown <= 0:
                if keys[c["soft_drop"]]:
                    self.soft_drop()
                self.v_move_cooldown = self.repeat_interval

        self.drop_timer += dt
        self.total_time += dt

        if self.is_on_ground(self.current_piece):
            self.lock_timer += dt
            if self.lock_timer >= LOCK_DELAY:
                self.lock_piece()
                self.spawn_new_piece()
        else:
            self.lock_timer = 0.0

        if self.drop_timer >= self.drop_interval:
            self.drop_timer = 0.0
            self.soft_drop()

    # -----------------------------------------------
    # Movement / rotation
    # -----------------------------------------------
    def _register_ground_touch(self) -> None:
        """
        Reset the lock timer, but only up to MAX_LOCK_RESETS times per piece.
        This is what fixes the "hold left/right forever and the piece never
        locks" bug: after enough resets, further moves/rotations no longer
        postpone the lock, so the piece is forced to settle.
        """
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

    _WALL_KICKS = _generate_wall_kicks()

    def rotate_piece(self, direction: int) -> None:
        """
        Rotate the piece in the given direction (1 for clockwise, -1 for
        counter-clockwise). If the rotation doesn't fit in place, try a
        series of wall-kick offsets (see _WALL_KICKS) until one fits, or
        give up and revert if none do.
        """
        old_rotation = self.current_piece.rotation_index
        old_x, old_y = self.current_piece.x, self.current_piece.y
        self.current_piece.rotate(direction)

        if not self._is_valid_position(self.current_piece):
            for dx, dy in self._WALL_KICKS:
                self.current_piece.x = old_x + dx
                self.current_piece.y = old_y + dy
                if self._is_valid_position(self.current_piece):
                    break
                self.current_piece.x, self.current_piece.y = old_x, old_y
            else:
                self.current_piece.rotation_index = old_rotation
                self.current_piece.x, self.current_piece.y = old_x, old_y
                return

        if self.is_on_ground(self.current_piece):
            self._register_ground_touch()

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
        self.hold_used_this_turn = True
        if self.held_piece is None:
            self.held_piece = self.current_piece
            self.spawn_new_piece()
        else:
            temp = self.current_piece
            self.current_piece = self.held_piece
            self.held_piece = temp
            self.current_piece.x = 3
            self.current_piece.y = 0
            self.current_piece.rotation_index = 0
            if not self._is_valid_position(self.current_piece):
                self.game_over = True
        self.lock_timer = 0.0
        self.lock_resets = 0

    def spawn_new_piece(self) -> None:
        if len(self.upcoming_pieces) < 7:
            self._generate_new_bag()
        self.current_piece = self.upcoming_pieces.pop(0)
        self.hold_used_this_turn = False
        self.lock_timer = 0.0
        self.lock_resets = 0
        if not self._is_valid_position(self.current_piece):
            self.game_over = True

    def lock_piece(self) -> None:
        for x, y in self.current_piece.get_blocks():
            if 0 <= y < GRID_HEIGHT and 0 <= x < GRID_WIDTH:
                self.board[y][x] = self.current_piece.color
        self.clear_lines()
        if self.line_target is not None and self.lines_cleared >= self.line_target:
            self.cleared = True
            self.game_over = True

    def clear_lines(self) -> None:
        full_rows = []
        for row_idx in range(GRID_HEIGHT):
            if all(self.board[row_idx][col_idx] is not None for col_idx in range(GRID_WIDTH)):
                full_rows.append(row_idx)
        for row_idx in full_rows:
            del self.board[row_idx]
            self.board.insert(0, [None for _ in range(GRID_WIDTH)])
        self.lines_cleared += len(full_rows)

    def _is_valid_position(self, piece: Tetromino) -> bool:
        for x, y in piece.get_blocks():
            if x < 0 or x >= GRID_WIDTH or y < 0 or y >= GRID_HEIGHT:
                return False
            if self.board[y][x] is not None:
                return False
        return True

    def is_on_ground(self, piece: Tetromino) -> bool:
        for x, y in piece.get_blocks():
            if y + 1 >= GRID_HEIGHT or self.board[y + 1][x] is not None:
                return True
        return False

    # -----------------------------------------------
    # Drawing
    # -----------------------------------------------
    def draw(self, screen: pygame.Surface, font_small: pygame.font.Font, font_med: pygame.font.Font) -> None:
        screen.fill(BLACK)

        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                cell_color = self.board[y][x]
                rect = pygame.Rect(
                    BOARD_X + x * BLOCK_SIZE,
                    BOARD_Y + y * BLOCK_SIZE,
                    BLOCK_SIZE, BLOCK_SIZE
                )
                if cell_color:
                    pygame.draw.rect(screen, cell_color, rect)
                    pygame.draw.rect(screen, WHITE, rect, 1)
                else:
                    pygame.draw.rect(screen, DARK_GRAY, rect, 1)

        self._draw_ghost_piece(screen)

        for x, y in self.current_piece.get_blocks():
            if y >= 0:
                rect = pygame.Rect(
                    BOARD_X + x * BLOCK_SIZE,
                    BOARD_Y + y * BLOCK_SIZE,
                    BLOCK_SIZE, BLOCK_SIZE
                )
                pygame.draw.rect(screen, self.current_piece.color, rect)
                pygame.draw.rect(screen, WHITE, rect, 1)

        # Board outline
        board_rect = pygame.Rect(BOARD_X, BOARD_Y, GRID_WIDTH * BLOCK_SIZE, GRID_HEIGHT * BLOCK_SIZE)
        pygame.draw.rect(screen, WHITE, board_rect, 2)

        self._draw_hold_area(screen, font_small)
        self._draw_next_pieces(screen, font_small)
        self._draw_stats(screen, font_small)

    def _draw_ghost_piece(self, screen: pygame.Surface) -> None:
        ghost = Tetromino(self.current_piece.shape)
        ghost.x = self.current_piece.x
        ghost.y = self.current_piece.y
        ghost.rotation_index = self.current_piece.rotation_index
        while self._is_valid_position(ghost):
            ghost.y += 1
        ghost.y -= 1
        for (x, y) in ghost.get_blocks():
            if y >= 0:
                rect = pygame.Rect(
                    BOARD_X + x * BLOCK_SIZE,
                    BOARD_Y + y * BLOCK_SIZE,
                    BLOCK_SIZE, BLOCK_SIZE
                )
                pygame.draw.rect(screen, GHOST_COLOR, rect)
                pygame.draw.rect(screen, WHITE, rect, 1)

    def _draw_mini_piece(self, screen, shape, color, offset_x, offset_y):
        coords = TETROMINOES[shape][0]
        min_x = min(cx for cx, _ in coords)
        min_y = min(cy for _, cy in coords)
        for cx, cy in coords:
            rx = offset_x + (cx - min_x) * (BLOCK_SIZE // 2)
            ry = offset_y + (cy - min_y) * (BLOCK_SIZE // 2)
            rect = pygame.Rect(rx, ry, BLOCK_SIZE // 2, BLOCK_SIZE // 2)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, WHITE, rect, 1)

    def _draw_hold_area(self, screen, font) -> None:
        text_surf = font.render("HOLD", True, WHITE)
        screen.blit(text_surf, (HOLD_AREA_X, HOLD_AREA_Y - 30))
        if self.held_piece:
            self._draw_mini_piece(screen, self.held_piece.shape, self.held_piece.color,
                                   HOLD_AREA_X + 20, HOLD_AREA_Y + 20)

    def _draw_next_pieces(self, screen, font) -> None:
        text_surf = font.render("NEXT", True, WHITE)
        screen.blit(text_surf, (NEXT_AREA_X, NEXT_AREA_Y - 30))
        for i in range(NUM_NEXT_PIECES):
            if i < len(self.upcoming_pieces):
                piece = self.upcoming_pieces[i]
                offset_x = NEXT_AREA_X
                offset_y = NEXT_AREA_Y + (i * 65)
                self._draw_mini_piece(screen, piece.shape, piece.color, offset_x, offset_y)

    def _draw_stats(self, screen, font) -> None:
        if self.line_target is not None:
            lines_str = f"Lines: {min(self.lines_cleared, self.line_target)}/{self.line_target}"
        else:
            lines_str = f"Lines: {self.lines_cleared}"
        lines_text = font.render(lines_str, True, WHITE)

        minutes = int(self.total_time // 60)
        seconds = int(self.total_time % 60)
        millis = int((self.total_time * 100) % 100)
        time_text = font.render(f"Time: {minutes}:{seconds:02d}.{millis:02d}", True, WHITE)

        mode_label = "40-Line Sprint" if self.mode == "sprint" else "Endless Mode"
        mode_text = font.render(mode_label, True, (180, 180, 180))

        screen.blit(mode_text, (HOLD_AREA_X, HOLD_AREA_Y + 130))
        screen.blit(lines_text, (HOLD_AREA_X, HOLD_AREA_Y + 160))
        screen.blit(time_text, (HOLD_AREA_X, HOLD_AREA_Y + 190))


class App:
    """
    Top-level state machine: TITLE -> MENU -> (CONTROLS | PLAYING) ->
    PAUSED / GAME_OVER, looping back around as needed. Owns the single
    pygame event loop -- this is what makes pause, the title screen and
    the menu all work cleanly instead of nested blocking loops.
    """

    STATE_TITLE = "TITLE"
    STATE_MENU = "MENU"
    STATE_CONTROLS = "CONTROLS"
    STATE_PLAYING = "PLAYING"
    STATE_PAUSED = "PAUSED"
    STATE_GAME_OVER = "GAME_OVER"

    def __init__(self) -> None:
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Tetris")
        self.clock = pygame.time.Clock()

        # NOTE: we deliberately do NOT call pygame.key.set_repeat() here.
        # Movement repeat is handled manually inside TetrisGame, and
        # rotate/hold/hard-drop are only ever triggered once per KEYDOWN,
        # which is what fixes the "holding rotate spams rotation" bug.

        self.font_title = pygame.font.SysFont("Arial", 64, bold=True)
        self.font_big = pygame.font.SysFont("Arial", 36, bold=True)
        self.font_med = pygame.font.SysFont("Arial", 26)
        self.font_small = pygame.font.SysFont("Arial", 20)

        self.controls: Dict[str, int] = dict(DEFAULT_CONTROLS)

        self.state = App.STATE_TITLE
        self.running = True

        self.menu_options = ["40-Line Sprint", "Endless Mode", "Controls", "Quit"]
        self.menu_index = 0

        self.pause_options = ["Resume", "Restart", "Main Menu"]
        self.pause_index = 0

        self.gameover_index = 0  # 0 = Yes (continue), 1 = No (main menu)

        self.controls_index = 0  # index into ACTION_ORDER + ["Back"]
        self.rebinding_action: Optional[str] = None

        self.current_mode = "sprint"
        self.game: Optional[TetrisGame] = None

    # -----------------------------------------------
    # Main loop
    # -----------------------------------------------
    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events(dt)
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()

    def start_game(self, mode: str) -> None:
        self.current_mode = mode
        self.game = TetrisGame(mode, self.controls)
        self.state = App.STATE_PLAYING

    # -----------------------------------------------
    # Events
    # -----------------------------------------------
    def handle_events(self, dt: float) -> None:
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
            elif choice == "Controls":
                self.state = App.STATE_CONTROLS
                self.controls_index = 0
            elif choice == "Quit":
                self.running = False

    def _handle_controls_event(self, event: pygame.event.Event) -> None:
        total_rows = len(ACTION_ORDER) + 1  # + "Back"
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
                self.state = App.STATE_MENU
            else:
                self.rebinding_action = ACTION_ORDER[self.controls_index]
        elif event.key == pygame.K_ESCAPE:
            self.state = App.STATE_MENU

    def _handle_pause_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == self.controls["pause"]:
            self.state = App.STATE_PLAYING
            return
        if event.key == pygame.K_UP:
            self.pause_index = (self.pause_index - 1) % len(self.pause_options)
        elif event.key == pygame.K_DOWN:
            self.pause_index = (self.pause_index + 1) % len(self.pause_options)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            choice = self.pause_options[self.pause_index]
            if choice == "Resume":
                self.state = App.STATE_PLAYING
            elif choice == "Restart":
                self.start_game(self.current_mode)
            elif choice == "Main Menu":
                self.game = None
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

    # -----------------------------------------------
    # Update
    # -----------------------------------------------
    def update(self, dt: float) -> None:
        if self.state == App.STATE_PLAYING and self.game is not None:
            keys = pygame.key.get_pressed()
            self.game.update(dt, keys)
            if self.game.game_over:
                self.gameover_index = 0
                self.state = App.STATE_GAME_OVER

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
        elif self.state == App.STATE_PLAYING:
            self.game.draw(self.screen, self.font_small, self.font_med)
        elif self.state == App.STATE_PAUSED:
            self.game.draw(self.screen, self.font_small, self.font_med)
            self._draw_pause_overlay()
        elif self.state == App.STATE_GAME_OVER:
            self._draw_game_over()

        pygame.display.flip()

    def _draw_title(self) -> None:
        self.screen.fill(BLACK)
        title_surf = self.font_title.render("TETRIS", True, CYAN)
        self.screen.blit(title_surf, ((WINDOW_WIDTH - title_surf.get_width()) // 2, 220))

        prompt_surf = self.font_med.render("Press any key to continue", True, WHITE)
        self.screen.blit(prompt_surf, ((WINDOW_WIDTH - prompt_surf.get_width()) // 2, 340))

        hint_surf = self.font_small.render("40-Line Sprint  |  Endless Mode  |  Customizable Controls",
                                            True, GRAY)
        self.screen.blit(hint_surf, ((WINDOW_WIDTH - hint_surf.get_width()) // 2, 400))

    def _draw_menu(self) -> None:
        self.screen.fill(BLACK)
        title_surf = self.font_big.render("MAIN MENU", True, WHITE)
        self.screen.blit(title_surf, ((WINDOW_WIDTH - title_surf.get_width()) // 2, 100))

        start_y = 230
        gap = 60
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
        self.screen.blit(hint_surf, ((WINDOW_WIDTH - hint_surf.get_width()) // 2, 600))

    def _draw_controls(self) -> None:
        self.screen.fill(BLACK)
        title_surf = self.font_big.render("CONTROLS", True, WHITE)
        self.screen.blit(title_surf, ((WINDOW_WIDTH - title_surf.get_width()) // 2, 50))

        start_y = 150
        gap = 45
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
        self.screen.blit(hint_surf, ((WINDOW_WIDTH - hint_surf.get_width()) // 2, 640))

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
        # Scale down if header too wide
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