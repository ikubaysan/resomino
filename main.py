import pygame
import sys
import random
from typing import List, Tuple, Optional, Dict, Callable

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

FPS = 60
LOCK_DELAY = 0.5
MAX_LOCK_RESETS = 15

MOVE_REPEAT_INITIAL_DELAY = 0.2
MOVE_REPEAT_INTERVAL = 0.05

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
            category = 0 if dy == 0 else (1 if dx == 0 else 2)
            return (category, 0 if dx < 0 else 1, 0 if dy < 0 else 1)

        candidates.sort(key=sort_key)
        kicks.extend(candidates)
    return kicks


WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
DARK_GRAY = (40, 40, 40)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
RED = (220, 60, 60)
ORANGE = (255, 165, 0)


# ---------------------------------------------------
# Difficulty presets for the CPU opponent
# ---------------------------------------------------
DIFFICULTIES: Dict[str, Dict[str, float]] = {
    # think_time: reaction delay before the CPU starts moving a new piece
    # action_interval: delay between each individual move/rotate step
    # mistake_chance: probability the CPU picks a random (non-optimal) placement
    # use_hold: whether the CPU is allowed to use the hold slot strategically
    "Easy":   {"think_time": 0.55, "action_interval": 0.16, "mistake_chance": 0.35, "use_hold": False},
    "Medium": {"think_time": 0.30, "action_interval": 0.09, "mistake_chance": 0.15, "use_hold": True},
    "Hard":   {"think_time": 0.12, "action_interval": 0.05, "mistake_chance": 0.05, "use_hold": True},
    "Expert": {"think_time": 0.04, "action_interval": 0.02, "mistake_chance": 0.0,  "use_hold": True},
}
DIFFICULTY_ORDER = ["Easy", "Medium", "Hard", "Expert"]


class Tetromino:
    def __init__(self, shape: str):
        self.shape: str = shape
        self.rotation_index: int = 0
        self.x: int = 3
        self.y: int = 0
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
    its own -- callers drive it by calling handle_event()/update()/draw()
    each frame. Supports an optional "multiplayer" mode where line clears
    generate garbage attacks that are routed to an opponent via a callback.
    """

    def __init__(self, mode: str, controls: Dict[str, int],
                 multiplayer: bool = False, label: str = "") -> None:
        self.mode = mode  # "sprint", "endless", or "versus"
        self.line_target: Optional[int] = 40 if mode == "sprint" else None
        self.controls = controls
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
        self.drop_interval: float = 0.5

        self.lock_timer: float = 0.0
        self.lock_resets: int = 0

        self.game_over: bool = False
        self.cleared: bool = False

        self.hard_drop_held = False
        self.left_held = False
        self.right_held = False
        self.down_held = False
        self.h_move_cooldown = 0.0
        self.v_move_cooldown = 0.0
        self.initial_delay = MOVE_REPEAT_INITIAL_DELAY
        self.repeat_interval = MOVE_REPEAT_INTERVAL

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
        if self.multiplayer:
            self._apply_pending_garbage()
            if self.game_over:
                return
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
        for x, y in self.current_piece.get_blocks():
            if y >= 0:
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
    issues one primitive input at a time (rotate / move / hold / hard drop)
    at a pace set by the chosen difficulty. Lower difficulties react more
    slowly and occasionally choose a deliberately sub-optimal placement to
    simulate mistakes; higher difficulties react almost instantly and play
    close to optimally.
    """

    def __init__(self, game: TetrisGame, difficulty: str):
        self.game = game
        settings = DIFFICULTIES.get(difficulty, DIFFICULTIES["Medium"])
        self.think_time = settings["think_time"]
        self.action_interval = settings["action_interval"]
        self.mistake_chance = settings["mistake_chance"]
        self.use_hold_enabled = settings["use_hold"]

        self._target_piece = None
        self._target: Optional[dict] = None
        self._think_timer = 0.0
        self._action_timer = 0.0
        self._hold_committed = False
        self._step_count = 0

    def update(self, dt: float) -> None:
        game = self.game
        if game.game_over:
            return
        if game.current_piece is not self._target_piece:
            self._target_piece = game.current_piece
            self._target = self._decide_target()
            self._think_timer = 0.0
            self._action_timer = 0.0
            self._hold_committed = False
            self._step_count = 0

        self._think_timer += dt
        if self._think_timer < self.think_time:
            return

        self._action_timer += dt
        if self._action_timer < self.action_interval:
            return
        self._action_timer = 0.0
        self._step()

    def _step(self) -> None:
        game = self.game
        target = self._target
        if target is None:
            game.hard_drop()
            return

        self._step_count += 1
        if self._step_count > 60:
            # Safety valve: never let the CPU stall indefinitely.
            game.hard_drop()
            return

        if target["use_hold"] and not self._hold_committed:
            game.hold_piece()
            self._hold_committed = True
            self._target_piece = game.current_piece  # don't re-plan after our own hold
            return

        cur = game.current_piece
        if cur.rotation_index != target["rotation"]:
            game.rotate_piece(1)
            return
        if cur.x < target["x"]:
            game.move_piece(dx=1)
            return
        if cur.x > target["x"]:
            game.move_piece(dx=-1)
            return
        game.hard_drop()

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

                if not fits(0):
                    continue
                y = 0
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
            if 0 <= by < GRID_HEIGHT and 0 <= bx < GRID_WIDTH:
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
                # A "mistake" run also has a chance of skipping a planned hold,
                # like a human missing the timing.
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
    def __init__(self, p1_controls: Dict[str, int], opponent: str, difficulty: Optional[str] = None):
        self.opponent = opponent  # "human" or "cpu"
        self.difficulty = difficulty
        self.p1 = TetrisGame(mode="versus", controls=p1_controls, multiplayer=True, label="Player 1")
        if opponent == "human":
            self.p2 = TetrisGame(mode="versus", controls=DEFAULT_CONTROLS_P2, multiplayer=True, label="Player 2")
            self.ai: Optional[AIController] = None
        else:
            self.p2 = TetrisGame(mode="versus", controls=DEFAULT_CONTROLS_P2, multiplayer=True,
                                  label=f"CPU ({difficulty})")
            self.ai = AIController(self.p2, difficulty or "Medium")

        self.p1.garbage_callback = self.p2.add_garbage
        self.p2.garbage_callback = self.p1.add_garbage

        self.finished = False
        self.winner: Optional[str] = None

    def handle_event(self, event: pygame.event.Event) -> None:
        self.p1.handle_event(event)
        if self.ai is None:
            self.p2.handle_event(event)

    def update(self, dt: float, keys) -> None:
        if self.finished:
            return
        self.p1.update(dt, keys)
        if self.ai is not None:
            self.ai.update(dt)
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


class App:
    """
    Top-level state machine driving the single pygame event loop. Handles
    the title screen, main menu, controls remapping, single-player games,
    and the versus flow (mode selection -> optional difficulty select ->
    match -> result).
    """
    STATE_TITLE = "TITLE"
    STATE_MENU = "MENU"
    STATE_CONTROLS = "CONTROLS"
    STATE_VERSUS_MENU = "VERSUS_MENU"
    STATE_DIFFICULTY_MENU = "DIFFICULTY_MENU"
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
        self.state = App.STATE_TITLE
        self.running = True

        self.menu_options = ["40-Line Sprint", "Endless Mode", "Versus", "Controls", "Quit"]
        self.menu_index = 0

        self.versus_menu_options = ["Player vs Player", "Player vs CPU", "Back"]
        self.versus_menu_index = 0

        self.difficulty_menu_options = DIFFICULTY_ORDER + ["Back"]
        self.difficulty_menu_index = 0

        self.pause_options = ["Resume", "Restart", "Main Menu"]
        self.pause_index = 0
        self.gameover_index = 0
        self.controls_index = 0
        self.rebinding_action: Optional[str] = None

        self.current_mode = "sprint"
        self.game: Optional[TetrisGame] = None

        self.versus_match: Optional[VersusMatch] = None
        self.vs_opponent = "human"
        self.vs_difficulty: Optional[str] = None

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

    def start_versus(self, opponent: str, difficulty: Optional[str] = None) -> None:
        self.vs_opponent = opponent
        self.vs_difficulty = difficulty
        self.versus_match = VersusMatch(self.controls, opponent, difficulty)
        self.state = App.STATE_PLAYING_VS

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
            elif self.state == App.STATE_VERSUS_MENU:
                self._handle_versus_menu_event(event)
            elif self.state == App.STATE_DIFFICULTY_MENU:
                self._handle_difficulty_menu_event(event)
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
            elif choice == "Controls":
                self.state = App.STATE_CONTROLS
                self.controls_index = 0
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
                self.state = App.STATE_DIFFICULTY_MENU
                self.difficulty_menu_index = 0
            elif choice == "Back":
                self.state = App.STATE_MENU
        elif event.key == pygame.K_ESCAPE:
            self.state = App.STATE_MENU

    def _handle_difficulty_menu_event(self, event: pygame.event.Event) -> None:
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
            else:
                self.start_versus("cpu", choice)
        elif event.key == pygame.K_ESCAPE:
            self.state = App.STATE_VERSUS_MENU

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

    def _handle_pause_vs_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.state = App.STATE_PLAYING_VS
            return
        if event.key == pygame.K_UP:
            self.pause_index = (self.pause_index - 1) % len(self.pause_options)
        elif event.key == pygame.K_DOWN:
            self.pause_index = (self.pause_index + 1) % len(self.pause_options)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            choice = self.pause_options[self.pause_index]
            if choice == "Resume":
                self.state = App.STATE_PLAYING_VS
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
    # Update
    # -----------------------------------------------
    def update(self, dt: float) -> None:
        if self.state == App.STATE_PLAYING and self.game is not None:
            keys = pygame.key.get_pressed()
            self.game.update(dt, keys)
            if self.game.game_over:
                self.gameover_index = 0
                self.state = App.STATE_GAME_OVER
        elif self.state == App.STATE_PLAYING_VS and self.versus_match is not None:
            keys = pygame.key.get_pressed()
            self.versus_match.update(dt, keys)
            if self.versus_match.finished:
                self.state = App.STATE_VS_OVER

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
        elif self.state == App.STATE_VERSUS_MENU:
            self._draw_versus_menu()
        elif self.state == App.STATE_DIFFICULTY_MENU:
            self._draw_difficulty_menu()
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

    def _draw_title(self) -> None:
        self.screen.fill(BLACK)
        title_surf = self.font_title.render("TETRIS", True, CYAN)
        self.screen.blit(title_surf, ((WINDOW_WIDTH - title_surf.get_width()) // 2, 220))
        prompt_surf = self.font_med.render("Press any key to continue", True, WHITE)
        self.screen.blit(prompt_surf, ((WINDOW_WIDTH - prompt_surf.get_width()) // 2, 340))
        hint_surf = self.font_small.render(
            "40-Line Sprint  |  Endless Mode  |  Versus (PvP or CPU)  |  Customizable Controls",
            True, GRAY)
        self.screen.blit(hint_surf, ((WINDOW_WIDTH - hint_surf.get_width()) // 2, 400))

    def _draw_menu(self) -> None:
        self.screen.fill(BLACK)
        title_surf = self.font_big.render("MAIN MENU", True, WHITE)
        self.screen.blit(title_surf, ((WINDOW_WIDTH - title_surf.get_width()) // 2, 100))
        start_y = 220
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
        self.screen.blit(hint_surf, ((WINDOW_WIDTH - hint_surf.get_width()) // 2, 600))

    def _draw_versus_menu(self) -> None:
        self.screen.fill(BLACK)
        title_surf = self.font_big.render("VERSUS", True, WHITE)
        self.screen.blit(title_surf, ((WINDOW_WIDTH - title_surf.get_width()) // 2, 130))
        start_y = 260
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
        self.screen.blit(hint_surf, ((WINDOW_WIDTH - hint_surf.get_width()) // 2, 480))
        hint2_surf = self.font_small.render("Esc to go back", True, GRAY)
        self.screen.blit(hint2_surf, ((WINDOW_WIDTH - hint2_surf.get_width()) // 2, 600))

    def _draw_difficulty_menu(self) -> None:
        self.screen.fill(BLACK)
        title_surf = self.font_big.render("SELECT DIFFICULTY", True, WHITE)
        self.screen.blit(title_surf, ((WINDOW_WIDTH - title_surf.get_width()) // 2, 130))
        descriptions = {
            "Easy": "Slow reactions, frequent mistakes",
            "Medium": "Moderate speed, occasional mistakes",
            "Hard": "Fast, rarely makes mistakes",
            "Expert": "Near-instant, essentially optimal play",
            "Back": "",
        }
        start_y = 240
        gap = 60
        for i, option in enumerate(self.difficulty_menu_options):
            color = YELLOW if i == self.difficulty_menu_index else WHITE
            text_surf = self.font_med.render(option, True, color)
            x = (WINDOW_WIDTH - text_surf.get_width()) // 2
            y = start_y + i * gap
            if i == self.difficulty_menu_index:
                marker = self.font_med.render(">", True, YELLOW)
                self.screen.blit(marker, (x - 40, y))
            self.screen.blit(text_surf, (x, y))
            desc = descriptions.get(option, "")
            if desc:
                desc_surf = self.font_small.render(desc, True, GRAY)
                self.screen.blit(desc_surf, ((WINDOW_WIDTH - desc_surf.get_width()) // 2, y + 30))
        hint_surf = self.font_small.render("Esc to go back", True, GRAY)
        self.screen.blit(hint_surf, ((WINDOW_WIDTH - hint_surf.get_width()) // 2, 620))

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