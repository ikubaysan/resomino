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
HOLD_AREA_X = 20
HOLD_AREA_Y = 50

NEXT_AREA_X = WINDOW_WIDTH - 150
NEXT_AREA_Y = 50

FPS = 60
LOCK_DELAY = 0.5  # 0.5 seconds of "floor time" before piece locks

# Key repeat settings (in milliseconds)
MOVE_REPEAT_INITIAL_DELAY_MS = 200  # How long to hold before repeat starts
MOVE_REPEAT_INTERVAL_MS = 50        # How quickly repeated moves happen

# ---------------------------------------------------
# Tetromino Definitions
# ---------------------------------------------------
TETROMINOES = {
    "I": [
        [(0, 0), (1, 0), (2, 0), (3, 0)],   # rotation 0
        [(0, 0), (0, 1), (0, 2), (0, 3)],   # rotation 1
        [(0, 0), (1, 0), (2, 0), (3, 0)],   # rotation 2
        [(0, 0), (0, 1), (0, 2), (0, 3)],   # rotation 3
    ],
    "O": [
        [(0, 0), (1, 0), (0, 1), (1, 1)],
        [(0, 0), (1, 0), (0, 1), (1, 1)],
        [(0, 0), (1, 0), (0, 1), (1, 1)],
        [(0, 0), (1, 0), (0, 1), (1, 1)],
    ],
    "T": [
        [(0, 1), (1, 1), (2, 1), (1, 0)],  # UP
        [(1, 0), (1, 1), (1, 2), (2, 1)],  # RIGHT
        [(0, 0), (1, 0), (2, 0), (1, 1)],  # DOWN
        [(0, 1), (1, 1), (1, 0), (1, 2)],  # LEFT
    ],
    "S": [
        [(1, 0), (2, 0), (0, 1), (1, 1)],    # 0
        [(1, 0), (1, 1), (2, 1), (2, 2)],    # 1
        [(1, 1), (2, 1), (0, 2), (1, 2)],    # 2
        [(0, 0), (0, 1), (1, 1), (1, 2)],    # 3
    ],
    "Z": [
        [(0, 0), (1, 0), (1, 1), (2, 1)],       # 0
        [(1, -1), (1, 0), (0, 0), (0, 1)],      # 1
        [(0, 0), (1, 0), (1, 1), (2, 1)],       # 2
        [(1, -1), (1, 0), (0, 0), (0, 1)],      # 3
    ],
    "L": [
        [(0, 0), (0, 1), (0, 2), (1, 2)],  # UP
        [(0, 0), (1, 0), (2, 0), (0, 1)],  # RIGHT
        [(1, 0), (1, 1), (1, 2), (0, 0)],  # DOWN
        [(0, 1), (1, 1), (2, 1), (2, 0)],  # LEFT
    ],
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

# Ghost piece color (gray). Change if you like.
GHOST_COLOR = (100, 100, 100)


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

        # Enable key repeat for holding left/right
        pygame.key.set_repeat(MOVE_REPEAT_INITIAL_DELAY_MS, MOVE_REPEAT_INTERVAL_MS)

        self.clock = pygame.time.Clock()

        # Board 2D array: None means empty cell, otherwise store a color
        self.board: List[List[Optional[Tuple[int, int, int]]]] = [
            [None] * GRID_WIDTH for _ in range(GRID_HEIGHT)
        ]

        # Lines cleared
        self.lines_cleared = 0

        # Track total time in seconds
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
        self.drop_timer: float = 0
        self.drop_interval: float = 0.5  # seconds per auto-drop

        # Lock delay timers
        self.lock_timer: float = 0.0

        # Running game flag
        self.running: bool = True

        self.left_held = False
        self.right_held = False
        self.horizontal_move_cooldown = 0.0

        self.initial_delay = 0.2  # seconds before repeat starts
        self.repeat_interval = 0.05  # seconds between repeated moves


    def _generate_new_bag(self) -> None:
        shapes = list(TETROMINOES.keys())
        random.shuffle(shapes)
        for shape in shapes:
            self.upcoming_pieces.append(Tetromino(shape))

    def run(self) -> bool:
        """
        Main game loop. Returns True if the player chooses to play again,
        or False if they choose to exit.
        """
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0  # seconds per frame
            self.handle_events()
            self.update(dt)
            self.draw()

        # Once self.running is False, the game is over. Show popup.
        return self.show_game_over_dialog()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_z:
                    self.rotate_piece(-1)
                elif event.key == pygame.K_x:
                    self.rotate_piece(1)
                elif event.key == pygame.K_UP:
                    self.hard_drop()
                elif event.key == pygame.K_SPACE:
                    self.hold_piece()
                elif event.key == pygame.K_LEFT:
                    self.left_held = True
                    # Move immediately on first press:
                    self.move_piece(dx=-1)
                    self.horizontal_move_cooldown = self.initial_delay
                elif event.key == pygame.K_RIGHT:
                    self.right_held = True
                    # Move immediately on first press:
                    self.move_piece(dx=1)
                    self.horizontal_move_cooldown = self.initial_delay
                elif event.key == pygame.K_DOWN:
                    self.soft_drop()

            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:
                    self.left_held = False
                elif event.key == pygame.K_RIGHT:
                    self.right_held = False

    def update(self, dt: float) -> None:
        """
        Update all game logic (auto-drop, lock delay, clearing lines).
        This includes handling continuous movement for left/right.
        """
        # Handle horizontal movement (left/right) polling
        keys = pygame.key.get_pressed()

        if self.left_held or self.right_held:
            self.horizontal_move_cooldown -= dt
            if self.horizontal_move_cooldown <= 0:
                if self.left_held and keys[pygame.K_LEFT]:
                    self.move_piece(dx=-1)
                elif self.right_held and keys[pygame.K_RIGHT]:
                    self.move_piece(dx=1)
                self.horizontal_move_cooldown = self.repeat_interval

        # Auto-drop logic for the current piece
        self.drop_timer += dt
        self.total_time += dt  # track total game time

        # If piece is on the ground, handle lock delay
        if self.is_on_ground(self.current_piece):
            self.lock_timer += dt
            if self.lock_timer >= LOCK_DELAY:
                self.lock_piece()
                self.spawn_new_piece()
        else:
            # Reset lock timer if not on the ground
            self.lock_timer = 0.0

        # Auto soft-drop based on the drop timer
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

        # Draw ghost piece first
        self.draw_ghost_piece()

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

        # Draw lines cleared & time
        self.draw_stats()

        pygame.display.flip()

    def draw_ghost_piece(self) -> None:
        """
        Draw a 'ghost' version of the current piece to show
        where it would land if dropped.
        """
        # Make a temporary copy of the current piece
        ghost = Tetromino(self.current_piece.shape)
        ghost.x = self.current_piece.x
        ghost.y = self.current_piece.y
        ghost.rotation_index = self.current_piece.rotation_index

        # Move down until it's invalid, then move back up 1
        while self._is_valid_position(ghost):
            ghost.y += 1
        ghost.y -= 1

        # If the ghost is exactly the same position as the current piece
        # (meaning the piece is on ground already), we still draw it.
        # Typically Tetris does show it in place. But you can skip if you want.

        # Draw the ghost blocks
        for (x, y) in ghost.get_blocks():
            if y >= 0:  # only draw if in visible region
                rect = pygame.Rect(
                    BOARD_X + x * BLOCK_SIZE,
                    BOARD_Y + y * BLOCK_SIZE,
                    BLOCK_SIZE, BLOCK_SIZE
                )
                pygame.draw.rect(self.screen, GHOST_COLOR, rect)
                # Outline it
                pygame.draw.rect(self.screen, (255, 255, 255), rect, 1)

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

    def draw_stats(self) -> None:
        """
        Draw lines cleared and total time (m:ss) in the top-left corner.
        """
        font = pygame.font.SysFont("Arial", 20)
        lines_text = font.render(f"Lines: {self.lines_cleared}", True, (255, 255, 255))

        # Convert total_time to minutes:seconds
        minutes = int(self.total_time // 60)
        seconds = int(self.total_time % 60)
        time_text = font.render(f"Time: {minutes}:{seconds:02d}", True, (255, 255, 255))

        # Blit them in the top-left corner (below HOLD or so)
        self.screen.blit(lines_text, (HOLD_AREA_X, HOLD_AREA_Y + 130))
        self.screen.blit(time_text, (HOLD_AREA_X, HOLD_AREA_Y + 160))

    def move_piece(self, dx: int = 0, dy: int = 0) -> None:
        old_x, old_y = self.current_piece.x, self.current_piece.y
        self.current_piece.x += dx
        self.current_piece.y += dy

        if not self._is_valid_position(self.current_piece):
            self.current_piece.x, self.current_piece.y = old_x, old_y
        else:
            # If we successfully moved while on the ground, reset lock timer
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

            # Check validity; if invalid, game over
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

        # Remove full rows and insert empty rows on top
        for row_idx in full_rows:
            del self.board[row_idx]
            self.board.insert(0, [None for _ in range(GRID_WIDTH)])

        # Count them
        self.lines_cleared += len(full_rows)

    def _is_valid_position(self, piece: Tetromino) -> bool:
        for x, y in piece.get_blocks():
            if x < 0 or x >= GRID_WIDTH or y < 0 or y >= GRID_HEIGHT:
                return False
            if self.board[y][x] is not None:
                return False
        return True

    def is_on_ground(self, piece: Tetromino) -> bool:
        """
        Check if moving the piece 1 step down would be invalid,
        meaning it's 'resting' on the floor or on top of other blocks.
        """
        for x, y in piece.get_blocks():
            if y + 1 >= GRID_HEIGHT or self.board[y + 1][x] is not None:
                return True
        return False

    def show_game_over_dialog(self) -> bool:
        """
        Show a popup with game stats (lines cleared, total time),
        and ask if you want to play again. Yes is default.
        Returns True if "Yes," False if "No" or quit.
        """
        font_big = pygame.font.SysFont("Arial", 30, bold=True)
        font_small = pygame.font.SysFont("Arial", 24)

        # Convert total_time to m:ss
        minutes = int(self.total_time // 60)
        seconds = int(self.total_time % 60)

        # Prepare text surfaces
        game_over_text = font_big.render("GAME OVER", True, (255, 255, 255))
        lines_text = font_small.render(f"Lines cleared: {self.lines_cleared}", True, (255, 255, 255))
        time_text = font_small.render(f"Time: {minutes}:{seconds:02d}", True, (255, 255, 255))

        # We'll have two "buttons": Yes / No
        yes_text = font_small.render("Yes", True, (0, 0, 0))
        no_text = font_small.render("No", True, (0, 0, 0))

        # Selected button index: 0 for yes, 1 for no
        selected = 0

        # A simple loop to display the dialog and wait for user input
        dialog_running = True
        while dialog_running:
            self.clock.tick(15)  # slow down the loop for the dialog

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_LEFT, pygame.K_RIGHT]:
                        # Toggle between yes/no
                        selected = 1 - selected
                    elif event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                        # If "yes" selected
                        if selected == 0:
                            return True
                        else:
                            return False
                    elif event.key == pygame.K_ESCAPE:
                        return False

            # Draw dialog background
            self.screen.fill((0, 0, 0))

            # Blit "GAME OVER" near center
            gw = game_over_text.get_width()
            gh = game_over_text.get_height()
            self.screen.blit(game_over_text, ((WINDOW_WIDTH - gw) // 2, 100))

            # Blit stats
            lw = lines_text.get_width()
            self.screen.blit(lines_text, ((WINDOW_WIDTH - lw) // 2, 160))

            tw = time_text.get_width()
            self.screen.blit(time_text, ((WINDOW_WIDTH - tw) // 2, 190))

            # Draw Yes / No "buttons"
            # Highlight the selected one by drawing a rectangle
            yes_rect = pygame.Rect(WINDOW_WIDTH // 2 - 60, 250, 50, 30)
            no_rect = pygame.Rect(WINDOW_WIDTH // 2 + 10, 250, 50, 30)

            # Draw background for selected button
            if selected == 0:
                pygame.draw.rect(self.screen, (255, 255, 0), yes_rect)  # highlight yes
                pygame.draw.rect(self.screen, (128, 128, 128), no_rect)
            else:
                pygame.draw.rect(self.screen, (128, 128, 128), yes_rect)
                pygame.draw.rect(self.screen, (255, 255, 0), no_rect)  # highlight no

            # Blit text "Yes" / "No"
            self.screen.blit(yes_text, (yes_rect.x + 5, yes_rect.y + 2))
            self.screen.blit(no_text, (no_rect.x + 5, no_rect.y + 2))

            pygame.display.flip()

        # If somehow we exit that loop, return False
        return False


def main():
    while True:
        game = TetrisGame()
        play_again = game.run()
        if not play_again:
            break

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
