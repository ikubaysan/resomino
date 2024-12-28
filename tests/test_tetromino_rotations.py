import pygame
import pytest
from typing import List, Tuple

# Import TETROMINOES dictionary from the main script
from main import TETROMINOES, BLOCK_SIZE

def display_all_tetrominoes() -> None:
    """
    Display all tetrominoes and their rotations in a single window.
    Each column represents a piece, and each row represents a rotation.
    """
    # Initialize pygame
    pygame.init()

    # Colors
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    BLUE = (0, 0, 255)
    FONT_COLOR = (200, 200, 200)

    # Grid and window settings
    COLUMN_SPACING = 4  # Blocks between columns
    ROW_SPACING = 2     # Blocks between rows
    MARGIN_BLOCKS = 2   # Margin blocks around the grid

    columns = len(TETROMINOES)  # One column per piece
    rows = 4  # Each piece has 4 rotations
    total_width = (columns * (BLOCK_SIZE * (4 + COLUMN_SPACING))) + (MARGIN_BLOCKS * BLOCK_SIZE)
    total_height = (rows * (BLOCK_SIZE * (4 + ROW_SPACING))) + (MARGIN_BLOCKS * BLOCK_SIZE)

    # Set up the display
    screen = pygame.display.set_mode((total_width, total_height))
    pygame.display.set_caption("Tetromino Rotations Viewer")

    # Font for labels
    font = pygame.font.SysFont("Arial", 16)

    running = True
    while running:
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Clear the screen
        screen.fill(BLACK)

        # Draw all tetrominoes
        for col_idx, (shape, rotations) in enumerate(TETROMINOES.items()):
            for row_idx, blocks in enumerate(rotations):
                # Compute position of the top-left corner for this piece's rotation
                x_offset = MARGIN_BLOCKS * BLOCK_SIZE + col_idx * (BLOCK_SIZE * (4 + COLUMN_SPACING))
                y_offset = MARGIN_BLOCKS * BLOCK_SIZE + row_idx * (BLOCK_SIZE * (4 + ROW_SPACING))

                # Draw the blocks for this rotation
                for x, y in blocks:
                    rect = pygame.Rect(
                        x_offset + x * BLOCK_SIZE,
                        y_offset + y * BLOCK_SIZE,
                        BLOCK_SIZE,
                        BLOCK_SIZE
                    )
                    pygame.draw.rect(screen, BLUE, rect)
                    pygame.draw.rect(screen, WHITE, rect, 2)  # Border

                # Add labels for shape and rotation
                if row_idx == 0:  # Add the shape label once per column
                    shape_label = font.render(shape, True, FONT_COLOR)
                    screen.blit(shape_label, (x_offset, y_offset - BLOCK_SIZE))

                rotation_label = font.render(f"Rot {row_idx}", True, FONT_COLOR)
                screen.blit(rotation_label, (x_offset - BLOCK_SIZE, y_offset))

        # Update the display
        pygame.display.flip()

    # Quit pygame
    pygame.quit()


def test_display_all_tetrominoes():
    """
    Test that displays all tetrominoes in their rotations in a single window.
    """
    display_all_tetrominoes()
