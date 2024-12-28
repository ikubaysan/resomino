import pygame
import sys
import random
from typing import List, Tuple, Optional, Dict

pygame.init()

# ---------------------------------------------------
# Window and Board Settings
# ---------------------------------------------------
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 660

GRID_WIDTH = 10   # Tetris: 10 columns
GRID_HEIGHT = 20  # Tetris: 20 rows
BLOCK_SIZE = 30   # Each cell is 30×30 pixels

# We'll place the board at (BOARD_X, BOARD_Y)
BOARD_X = (WINDOW_WIDTH - GRID_WIDTH * BLOCK_SIZE) // 2
BOARD_Y = 30  # Some margin from the top

# Offsets for the "Hold" area and "Next" area
# so they are visible on the left and right sides
HOLD_AREA_X = 20
HOLD_AREA_Y = 50

NEXT_AREA_X = WINDOW_WIDTH - 150
NEXT_AREA_Y = 50

FPS = 60
LOCK_DELAY = 0.5  # 0.5 seconds of "floor time" before piece locks


# ---------------------------------------------------
# Tetromino Definitions
# ---------------------------------------------------
TETROMINOES = {
    # ----------------------------------------------------------------
    # I PIECE
    # ----------------------------------------------------------------
    #
    # Rotations (using a 4x1 or 1x4 bounding box):
    #
    # 0 (Horizontal):
    #  XXXX
    #  coords: (0,0),(1,0),(2,0),(3,0)
    #
    # 1 (Vertical):
    #  X
    #  X
    #  X
    #  X
    #  coords: (0,0),(0,1),(0,2),(0,3)
    #
    # 2 (Horizontal, same as 0):
    #  XXXX
    #
    # 3 (Vertical, same as 1):
    #  X
    #  X
    #  X
    #  X
    #
    "I": [
        [(0, 0), (1, 0), (2, 0), (3, 0)],   # rotation 0
        [(0, 0), (0, 1), (0, 2), (0, 3)],   # rotation 1
        [(0, 0), (1, 0), (2, 0), (3, 0)],   # rotation 2
        [(0, 0), (0, 1), (0, 2), (0, 3)],   # rotation 3
    ],

    # ----------------------------------------------------------------
    # O PIECE (square)
    # ----------------------------------------------------------------
    #
    # The square is the same in all 4 rotations:
    #
    #  XX
    #  XX
    #
    #  coords: (0,0),(1,0),(0,1),(1,1)
    #
    "O": [
        [(0, 0), (1, 0), (0, 1), (1, 1)],
        [(0, 0), (1, 0), (0, 1), (1, 1)],
        [(0, 0), (1, 0), (0, 1), (1, 1)],
        [(0, 0), (1, 0), (0, 1), (1, 1)],
    ],

    # ----------------------------------------------------------------
    # T PIECE
    # ----------------------------------------------------------------
    #
    # 0 (T UP):
    #    X
    #   XXX
    #  coords: (0,1),(1,1),(2,1),(1,0)
    #
    # 1 (T RIGHT):
    #    X
    #    XX
    #    X
    #  coords: (1,0),(1,1),(1,2),(2,1)
    #
    # 2 (T DOWN):
    #   XXX
    #    X
    #  coords: (0,0),(1,0),(2,0),(1,1)
    #
    # 3 (T LEFT):
    #     X
    #    XX
    #     X
    #  coords: (0,1),(1,1),(1,0),(1,2)
    #
    "T": [
        [(0, 1), (1, 1), (2, 1), (1, 0)],  # UP
        [(1, 0), (1, 1), (1, 2), (2, 1)],  # RIGHT
        [(0, 0), (1, 0), (2, 0), (1, 1)],  # DOWN
        [(0, 1), (1, 1), (1, 0), (1, 2)],  # LEFT
    ],

    # ----------------------------------------------------------------
    # S PIECE
    # ----------------------------------------------------------------
    #
    # Generally S has only 2 unique orientations, but we list 4
    # for consistency (the repeats can be used in some Tetris logic).
    #
    # 0 (Horizontal):
    #    XX
    #   XX
    #  coords: (1,0),(2,0),(0,1),(1,1)
    #
    # 1 (Vertical):
    #    X
    #    XX
    #     X
    #  coords: (1,0),(1,1),(2,1),(2,2)
    #
    # 2 (Horizontal, repeat):
    #    XX
    #   XX
    #
    # 3 (Vertical, alternate):
    #    X
    #    XX
    #     X
    #
    "S": [
        [(1, 0), (2, 0), (0, 1), (1, 1)],    # 0
        [(1, 0), (1, 1), (2, 1), (2, 2)],    # 1
        [(1, 1), (2, 1), (0, 2), (1, 2)],    # 2 (repeat or mirrored)
        [(0, 0), (0, 1), (1, 1), (1, 2)],    # 3 (alternate orientation)
    ],

    # ----------------------------------------------------------------
    # Z PIECE
    # ----------------------------------------------------------------
    #
    # Like S, Z also has 2 unique orientations, repeated/expanded to 4.
    #
    # 0 (Horizontal):
    #   XX
    #    XX
    #  coords: (0,0),(1,0),(1,1),(2,1)
    #
    # 1 (Vertical):
    #    X
    #   XX
    #   X
    #  coords: (1,-1),(1,0),(0,0),(0,1)
    #
    # 2 (Horizontal, repeat of 0):
    #   XX
    #    XX
    #
    # 3 (Vertical, repeat of 1):
    #    X
    #   XX
    #   X
    #
    "Z": [
        [(0, 0), (1, 0), (1, 1), (2, 1)],       # 0
        [(1, -1), (1, 0), (0, 0), (0, 1)],      # 1
        [(0, 0), (1, 0), (1, 1), (2, 1)],       # 2
        [(1, -1), (1, 0), (0, 0), (0, 1)],      # 3
    ],

    # ----------------------------------------------------------------
    # J PIECE
    # ----------------------------------------------------------------
    #
    # 0 (J UP):
    #   X
    #   X
    #  XX
    #  coords: (0,0),(0,1),(0,2),(1,2)
    #
    # 1 (J RIGHT):
    #  XXX
    #  X
    #  coords: (0,0),(1,0),(2,0),(0,1)
    #
    # 2 (J DOWN):
    #  XX
    #   X
    #   X
    #  coords: (1,0),(1,1),(1,2),(0,0)
    #
    # 3 (J LEFT):
    #    X
    #   XXX
    #  coords: (0,1),(1,1),(2,1),(2,0)
    #
    "L": [
        [(0, 0), (0, 1), (0, 2), (1, 2)],  # UP
        [(0, 0), (1, 0), (2, 0), (0, 1)],  # RIGHT
        [(1, 0), (1, 1), (1, 2), (0, 0)],  # DOWN
        [(0, 1), (1, 1), (2, 1), (2, 0)],  # LEFT
    ],

    # ----------------------------------------------------------------
    # L PIECE
    # ----------------------------------------------------------------
    #
    # 0 (L UP):
    #     X
    #     X
    #    XX
    #  coords: (1,0),(1,1),(1,2),(0,2)
    #
    # 1 (L RIGHT):
    #  XXX
    #    X
    #  coords: (0,0),(1,0),(2,0),(2,1)
    #
    # 2 (L DOWN):
    #  XX
    #  X
    #  X
    #  coords: (0,0),(0,1),(0,2),(1,0)
    #
    # 3 (L LEFT):
    #  X
    #  XXX
    #  coords: (0,0),(1,0),(2,0),(0,1)
    #
    "J": [
        [(1, 0), (1, 1), (1, 2), (0, 2)],  # UP
        [(0, 0), (0, 1), (1, 1), (2, 1)],  # RIGHT
        [(0, 0), (0, 1), (0, 2), (1, 0)],  # DOWN
        [(0, 0), (1, 0), (2, 0), (2, 1)],  # LEFT
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
        Rotate the piece in the given direction (1 for clockwise, -1 for counter-clockwise).
        """
        self.rotation_index = (self.rotation_index + direction) % len(TETROMINOES[self.shape])


class TetrisGame:
    def __init__(self) -> None:
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Tetris")

        self.clock = pygame.time.Clock()

        # Board 2D array: None means empty cell, otherwise store a color
        self.board: List[List[Optional[Tuple[int, int, int]]]] = [
            [None] * GRID_WIDTH for _ in range(GRID_HEIGHT)
        ]

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
        self.drop_timer: float = 0
        self.drop_interval: float = 0.5  # seconds per auto-drop

        # Lock delay timers
        self.lock_timer: float = 0.0
        self.running: bool = True

    def _generate_new_bag(self) -> None:
        shapes = list(TETROMINOES.keys())
        random.shuffle(shapes)
        for shape in shapes:
            self.upcoming_pieces.append(Tetromino(shape))

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0  # seconds per frame
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.move_piece(dx=-1)
                elif event.key == pygame.K_RIGHT:
                    self.move_piece(dx=1)
                elif event.key == pygame.K_DOWN:
                    self.soft_drop()
                elif event.key == pygame.K_UP:
                    self.hard_drop()
                elif event.key == pygame.K_SPACE:
                    self.hold_piece()
                elif event.key == pygame.K_z:
                    self.rotate_piece(-1)
                elif event.key == pygame.K_x:
                    self.rotate_piece(1)

    def update(self, dt: float) -> None:
        """
        Update all game logic (auto-drop, lock delay, clearing lines).
        """
        self.drop_timer += dt

        # Check if the piece is on the ground
        if self.is_on_ground(self.current_piece):
            # Start or continue the lock timer
            self.lock_timer += dt
            # If it has sat on the ground too long, lock it
            if self.lock_timer >= LOCK_DELAY:
                self.lock_piece()
                self.spawn_new_piece()
        else:
            # If not on the ground, reset the lock timer
            self.lock_timer = 0.0

        # Automatic soft drop
        if self.drop_timer >= self.drop_interval:
            self.drop_timer = 0
            self.soft_drop()

    def draw(self) -> None:
        self.screen.fill((0, 0, 0))

        # Draw the board (locked blocks)
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                cell_color = self.board[y][x]
                rect = pygame.Rect(
                    BOARD_X + x * BLOCK_SIZE,
                    BOARD_Y + y * BLOCK_SIZE,
                    BLOCK_SIZE, BLOCK_SIZE
                )
                # Draw cells
                if cell_color:
                    pygame.draw.rect(self.screen, cell_color, rect)
                    pygame.draw.rect(self.screen, (255, 255, 255), rect, 1)
                else:
                    # faint grid line
                    pygame.draw.rect(self.screen, (40, 40, 40), rect, 1)

        # Draw the current falling piece
        for x, y in self.current_piece.get_blocks():
            if y >= 0:  # only draw if in visible region
                rect = pygame.Rect(
                    BOARD_X + x * BLOCK_SIZE,
                    BOARD_Y + y * BLOCK_SIZE,
                    BLOCK_SIZE, BLOCK_SIZE
                )
                pygame.draw.rect(self.screen, self.current_piece.color, rect)
                pygame.draw.rect(self.screen, (255, 255, 255), rect, 1)

        # Draw hold piece on the left
        self.draw_hold_area()

        # Draw the next 2 upcoming pieces on the right
        self.draw_next_pieces()

        pygame.display.flip()

    def draw_hold_area(self) -> None:
        font = pygame.font.SysFont("Arial", 20)
        text_surf = font.render("HOLD", True, (255, 255, 255))
        self.screen.blit(text_surf, (HOLD_AREA_X, HOLD_AREA_Y - 30))

        if self.held_piece:
            # Always display the 0th rotation in the mini preview
            coords = TETROMINOES[self.held_piece.shape][0]
            color = self.held_piece.color
            # Center them in a small 4x4 region
            offset_x = HOLD_AREA_X + 20
            offset_y = HOLD_AREA_Y + 20

            # Find bounding box
            min_x = min(cx for cx, _ in coords)
            max_x = max(cx for cx, _ in coords)
            min_y = min(cy for _, cy in coords)
            max_y = max(cy for _, cy in coords)

            # We'll shift them to start around offset_x, offset_y
            for cx, cy in coords:
                rx = offset_x + (cx - min_x) * (BLOCK_SIZE // 2)
                ry = offset_y + (cy - min_y) * (BLOCK_SIZE // 2)
                rect = pygame.Rect(rx, ry, BLOCK_SIZE // 2, BLOCK_SIZE // 2)
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, (255, 255, 255), rect, 1)

    def draw_next_pieces(self) -> None:
        font = pygame.font.SysFont("Arial", 20)
        text_surf = font.render("NEXT", True, (255, 255, 255))
        self.screen.blit(text_surf, (NEXT_AREA_X, NEXT_AREA_Y - 30))

        # Show next 2 pieces
        for i in range(2):
            if i < len(self.upcoming_pieces):
                piece = self.upcoming_pieces[i]
                coords = TETROMINOES[piece.shape][0]  # show rotation 0
                color = piece.color

                offset_x = NEXT_AREA_X
                offset_y = NEXT_AREA_Y + (i * 80)

                # bounding box
                min_x = min(cx for cx, _ in coords)
                max_x = max(cx for cx, _ in coords)
                min_y = min(cy for _, cy in coords)
                max_y = max(cy for _, cy in coords)

                for (cx, cy) in coords:
                    rx = offset_x + (cx - min_x) * (BLOCK_SIZE // 2)
                    ry = offset_y + (cy - min_y) * (BLOCK_SIZE // 2)
                    rect = pygame.Rect(rx, ry, BLOCK_SIZE // 2, BLOCK_SIZE // 2)
                    pygame.draw.rect(self.screen, color, rect)
                    pygame.draw.rect(self.screen, (255, 255, 255), rect, 1)

    def move_piece(self, dx: int = 0, dy: int = 0) -> None:
        old_x, old_y = self.current_piece.x, self.current_piece.y
        self.current_piece.x += dx
        self.current_piece.y += dy

        if not self._is_valid_position(self.current_piece):
            self.current_piece.x, self.current_piece.y = old_x, old_y
        else:
            # If we successfully moved while on the ground, reset lock timer
            # (typical Tetris resets lock delay on any move or rotation)
            if self.is_on_ground(self.current_piece):
                self.lock_timer = 0.0

    def rotate_piece(self, direction: int) -> None:
        old_rotation = self.current_piece.rotation_index
        self.current_piece.rotate(direction)

        if not self._is_valid_position(self.current_piece):
            self.current_piece.rotation_index = old_rotation
        else:
            # Reset lock timer if on ground
            if self.is_on_ground(self.current_piece):
                self.lock_timer = 0.0

    def soft_drop(self) -> None:
        old_y = self.current_piece.y
        self.current_piece.y += 1
        if not self._is_valid_position(self.current_piece):
            self.current_piece.y = old_y
            # We do NOT immediately lock here; lock delay handles it
            return
        else:
            # If we drop onto the ground, reset lock timer
            if self.is_on_ground(self.current_piece):
                self.lock_timer = 0.0

    def hard_drop(self) -> None:
        while self._is_valid_position(self.current_piece):
            self.current_piece.y += 1
        # Overshoot
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
            # Reset the newly active piece to top
            self.current_piece.x = 3
            self.current_piece.y = 0
            self.current_piece.rotation_index = 0

            # Check validity; if invalid, game over or revert
            if not self._is_valid_position(self.current_piece):
                self.running = False

        # Reset lock timer because we have a new piece
        self.lock_timer = 0.0

    def spawn_new_piece(self) -> None:
        if len(self.upcoming_pieces) < 7:
            self._generate_new_bag()

        self.current_piece = self.upcoming_pieces.pop(0)
        self.hold_used_this_turn = False
        self.lock_timer = 0.0
        # If the piece spawns in an invalid position -> game over
        if not self._is_valid_position(self.current_piece):
            self.running = False

    def lock_piece(self) -> None:
        for x, y in self.current_piece.get_blocks():
            if 0 <= y < GRID_HEIGHT and 0 <= x < GRID_WIDTH:
                self.board[y][x] = self.current_piece.color
        self.clear_lines()

    def clear_lines(self) -> None:
        full_rows = []
        for row_idx in range(GRID_HEIGHT):
            if all(self.board[row_idx][col_idx] is not None for col_idx in range(GRID_WIDTH)):
                full_rows.append(row_idx)

        for row_idx in full_rows:
            del self.board[row_idx]
            self.board.insert(0, [None for _ in range(GRID_WIDTH)])

    def _is_valid_position(self, piece: Tetromino) -> bool:
        for x, y in piece.get_blocks():
            if x < 0 or x >= GRID_WIDTH or y < 0 or y >= GRID_HEIGHT:
                return False
            if self.board[y][x] is not None:
                return False
        return True

    def is_on_ground(self, piece: Tetromino) -> bool:
        """
        Check if the piece is at a position where moving one step down
        would be invalid (meaning it's 'resting' on the floor or on top of other blocks).
        """
        for x, y in piece.get_blocks():
            # If directly below is out of board or occupied
            if y + 1 >= GRID_HEIGHT or self.board[y + 1][x] is not None:
                return True
        return False


def main():
    game = TetrisGame()
    game.run()


if __name__ == "__main__":
    main()
