import pygame
import serial
import random
import sys
import pygame.gfxdraw  # For anti-aliased drawing

# === Configuration ===
WIDTH, HEIGHT = 800, 600  # Larger window for better visuals
CELL_SIZE = 20
FPS = 7  # Further reduced base speed for slower snake
DEAD_ZONE = 150  # Joystick dead zone

# Colors (Jungle theme)
BG_COLOR = (10, 50, 20)  # Dark green
GRID_COLOR = (20, 80, 40)  # Subtle green lines
SNAKE_COLOR = (50, 200, 100)  # Scaled green
FOOD_COLOR = (255, 200, 0)  # Golden orb
TEXT_COLOR = (230, 230, 230)
TITLE_COLOR = (0, 200, 255)
POWERUP_COLOR = (0, 100, 255)  # Blue for power-ups

# Arduino serial port config
ARDUINO_PORT = 'COM9'
BAUD_RATE = 9600

# Initialize Pygame, font, and mixer for sounds
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Super Noah-Snake-Game")
clock = pygame.time.Clock()
font = pygame.font.SysFont('Segoe UI', 28)
title_font = pygame.font.SysFont('Segoe UI', 36, bold=True)
small_font = pygame.font.SysFont('Segoe UI', 20)

# Load sounds (download free SFX and place in same folder)
try:
    eat_sound = pygame.mixer.Sound('chomp.wav')  # Chomp sound on eat
    game_over_sound = pygame.mixer.Sound('buzz.wav')  # Buzz on game over
    powerup_sound = pygame.mixer.Sound('powerup.wav')  # Ding for power-up
except FileNotFoundError:
    eat_sound = game_over_sound = powerup_sound = None  # Fallback if no files

# Optional background image (create/download 'jungle_bg.png')
try:
    background_image = pygame.image.load('jungle_bg.png')
    background_image = pygame.transform.scale(background_image, (WIDTH, HEIGHT))
except FileNotFoundError:
    background_image = None

# Initialize Serial
try:
    ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=0.1)
except serial.SerialException:
    print(f"Error: Cannot connect to Arduino on {ARDUINO_PORT}. Falling back to keyboard controls.")
    ser = None  # Fallback to keyboard if no serial

# High score file
HIGH_SCORE_FILE = 'highscore.txt'
try:
    with open(HIGH_SCORE_FILE, 'r') as f:
        high_score = int(f.read())
except FileNotFoundError:
    high_score = 0

def save_high_score(score):
    global high_score
    if score > high_score:
        high_score = score
        with open(HIGH_SCORE_FILE, 'w') as f:
            f.write(str(high_score))

def draw_text(text, font, color, surface, x, y, center=False):
    txt_obj = font.render(text, True, color)
    txt_rect = txt_obj.get_rect()
    if center:
        txt_rect.center = (x, y)
    else:
        txt_rect.topleft = (x, y)
    surface.blit(txt_obj, txt_rect)

def random_food_position(snake, obstacles):
    while True:
        x = random.randint(0, (WIDTH // CELL_SIZE) - 1)
        y = random.randint(0, (HEIGHT // CELL_SIZE) - 1)
        pos = (x * CELL_SIZE, y * CELL_SIZE)
        if pos not in snake and pos not in obstacles:
            return pos

def draw_grid():
    for x in range(0, WIDTH, CELL_SIZE):
        pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, CELL_SIZE):
        pygame.draw.line(screen, GRID_COLOR, (0, y), (WIDTH, y))

# Game variables
snake = [(WIDTH // 2, HEIGHT // 2)]
direction = (0, 0)
food_pos = random_food_position(snake, [])
food_type = 'normal'  # 'normal' or 'power'
score = 0
game_over = False
paused = False
show_grid = True
level = 1
obstacles = []  # For higher levels
powerup_active = False
powerup_timer = 0
particles = []  # For eat effects

# Joystick calibration (assume center is 512; adjust if needed)
joy_center_x, joy_center_y = 512, 512

def get_direction():
    global direction, paused
    if ser:  # Joystick mode
        try:
            data = ser.readline().decode().strip()
            if data:  # Ensure data is not empty
                values = data.split(',')
                if len(values) == 3:  # Expect X,Y,B
                    joyX = int(values[0]) - joy_center_x
                    joyY = int(values[1]) - joy_center_y
                    button = int(values[2])
                    print(f"Joystick: X={joyX}, Y={joyY}, Button={button}")  # Debug print

                    if button == 0:  # Button pressed (LOW due to pull-up)
                        paused = not paused

                    dx, dy = 0, 0
                    if abs(joyX) > DEAD_ZONE:
                        dx = 1 if joyX > 0 else -1
                    if abs(joyY) > DEAD_ZONE:
                        dy = 1 if joyY > 0 else -1

                    # No diagonals
                    if dx != 0:
                        dy = 0

                    return (dx, dy)
                else:
                    print(f"Invalid serial data: {data}")  # Debug
        except (ValueError, UnicodeDecodeError) as e:
            print(f"Serial error: {e}")  # Debug
        return direction  # Fallback to current direction
    else:  # Keyboard fallback
        keys = pygame.key.get_pressed()
        dx, dy = direction
        if keys[pygame.K_LEFT]:
            dx, dy = -1, 0
        elif keys[pygame.K_RIGHT]:
            dx, dy = 1, 0
        elif keys[pygame.K_UP]:
            dx, dy = 0, -1
        elif keys[pygame.K_DOWN]:
            dx, dy = 0, 1
        if keys[pygame.K_p]:
            paused = not paused
        return (dx, dy)

# Menu screen
def show_menu():
    screen.fill(BG_COLOR)
    if background_image:
        screen.blit(background_image, (0, 0))
    draw_text("Super Noah-Snake-Game", title_font, TITLE_COLOR, screen, WIDTH // 2, HEIGHT // 4, center=True)
    draw_text("Use joystick (or arrows) to move", small_font, TEXT_COLOR, screen, WIDTH // 2, HEIGHT // 2 - 50, center=True)
    draw_text("Eat golden orbs to grow! Avoid edges and self.", small_font, TEXT_COLOR, screen, WIDTH // 2, HEIGHT // 2, center=True)
    draw_text("Power-ups: Blue orbs for speed boost!", small_font, TEXT_COLOR, screen, WIDTH // 2, HEIGHT // 2 + 50, center=True)
    draw_text("Press SPACE to start", font, FOOD_COLOR, screen, WIDTH // 2, HEIGHT // 2 + 150, center=True)
    pygame.display.flip()

# Show menu at start
show_menu()
waiting = True
while waiting:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()
    keys = pygame.key.get_pressed()
    if keys[pygame.K_SPACE] or get_direction() != (0, 0):  # Start on key or joystick move
        waiting = False

while True:
    screen.fill(BG_COLOR)
    if background_image:
        screen.blit(background_image, (0, 0))
    if show_grid:
        draw_grid()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if ser:
                ser.close()
            save_high_score(score)
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_g:
                show_grid = not show_grid
            if event.key == pygame.K_p:
                paused = not paused
            if event.key == pygame.K_f:
                pygame.display.toggle_fullscreen()

    if paused:
        draw_text("Paused", title_font, TEXT_COLOR, screen, WIDTH // 2, HEIGHT // 2, center=True)
        pygame.display.flip()
        clock.tick(5)
        continue

    if not game_over:
        new_dir = get_direction()
        # Prevent reversing
        if (new_dir[0] * -1, new_dir[1] * -1) != direction and new_dir != (0, 0):
            direction = new_dir

        if direction != (0, 0):
            new_head = (snake[0][0] + direction[0] * CELL_SIZE,
                        snake[0][1] + direction[1] * CELL_SIZE)

            # Wall collision
            if (new_head[0] < 0 or new_head[0] >= WIDTH or
                new_head[1] < 0 or new_head[1] >= HEIGHT):
                game_over = True
                if game_over_sound:
                    game_over_sound.play()

            # Self or obstacle collision (unless powerup active)
            if not powerup_active and (new_head in snake or new_head in obstacles):
                game_over = True
                if game_over_sound:
                    game_over_sound.play()

            snake.insert(0, new_head)

            # Eat food
            if new_head == food_pos:
                score += 1
                save_high_score(score)
                if eat_sound:
                    eat_sound.play()
                # Particles for effect
                food_center = (food_pos[0] + CELL_SIZE // 2, food_pos[1] + CELL_SIZE // 2)
                for _ in range(20):
                    particles.append([[food_center[0], food_center[1]], [random.randint(-5, 5), random.randint(-5, 5)], random.randint(10, 20)])
                if food_type == 'power':
                    powerup_active = True
                    powerup_timer = 105  # ~15 seconds at 7 FPS
                    if powerup_sound:
                        powerup_sound.play()
                    FPS = 10  # Further reduced speed boost
                else:
                    # Grow (don't pop tail)
                    pass
                # Spawn new food, 10% chance power-up
                food_pos = random_food_position(snake, obstacles)
                food_type = 'power' if random.random() < 0.1 else 'normal'
            else:
                snake.pop()

            # Level progression
            if score // 10 + 1 > level:
                level = score // 10 + 1
                FPS += 0.5  # Reduced speed increment
                # Add obstacles
                for _ in range(level):
                    obstacles.append(random_food_position(snake, obstacles))  # Random walls

        # Power-up timer
        if powerup_active:
            powerup_timer -= 1
            if powerup_timer <= 0:
                powerup_active = False
                FPS = 7  # Reset to further reduced base speed

    # Draw obstacles as rocks (gray circles)
    for obs in obstacles:
        obs_center = (obs[0] + CELL_SIZE // 2, obs[1] + CELL_SIZE // 2)
        pygame.gfxdraw.filled_circle(screen, *obs_center, CELL_SIZE // 2, (100, 100, 100))

    # Draw food
    food_center = (food_pos[0] + CELL_SIZE // 2, food_pos[1] + CELL_SIZE // 2)
    color = POWERUP_COLOR if food_type == 'power' else FOOD_COLOR
    pygame.gfxdraw.filled_circle(screen, *food_center, CELL_SIZE // 2, color)
    pygame.gfxdraw.aacircle(screen, *food_center, CELL_SIZE // 2 - 2, (255, 255, 255))  # Shine

    # Draw snake
    for i, segment in enumerate(snake):
        seg_center = (segment[0] + CELL_SIZE // 2, segment[1] + CELL_SIZE // 2)
        radius = CELL_SIZE // 2 - (i // len(snake) * 2)  # Slight taper
        snake_color = SNAKE_COLOR if not powerup_active else (255, 255, 0)  # Glow if powerup
        pygame.gfxdraw.filled_circle(screen, *seg_center, radius, snake_color)
        if i == 0:  # Head with eyes
            eye_offset = CELL_SIZE // 4
            eye_color = (255, 255, 255)
            if direction[0] > 0:  # Right
                eyes = [(seg_center[0] + eye_offset, seg_center[1] - eye_offset // 2), (seg_center[0] + eye_offset, seg_center[1] + eye_offset // 2)]
            elif direction[0] < 0:  # Left
                eyes = [(seg_center[0] - eye_offset, seg_center[1] - eye_offset // 2), (seg_center[0] - eye_offset, seg_center[1] + eye_offset // 2)]
            elif direction[1] > 0:  # Down
                eyes = [(seg_center[0] - eye_offset // 2, seg_center[1] + eye_offset), (seg_center[0] + eye_offset // 2, seg_center[1] + eye_offset)]
            else:  # Up or still
                eyes = [(seg_center[0] - eye_offset // 2, seg_center[1] - eye_offset), (seg_center[0] + eye_offset // 2, seg_center[1] - eye_offset)]
            for eye in eyes:
                pygame.gfxdraw.filled_circle(screen, *eye, 3, eye_color)

    # Draw particles
    for p in particles[:]:
        pygame.draw.circle(screen, FOOD_COLOR, (int(p[0][0]), int(p[0][1])), p[2] // 2)
        p[0][0] += p[1][0]
        p[0][1] += p[1][1]
        p[2] -= 1
        if p[2] <= 0:
            particles.remove(p)

    # HUD
    draw_text("Super Noah-Snake-Game", title_font, TITLE_COLOR, screen, 10, 10)
    draw_text(f"Score: {score} | High: {high_score} | Level: {level}", font, TEXT_COLOR, screen, 10, HEIGHT - 40)
    if powerup_active:
        draw_text("Power-Up Active!", small_font, POWERUP_COLOR, screen, WIDTH - 200, 10)

    if game_over:
        screen.fill((100, 0, 0, 100), special_flags=pygame.BLEND_RGBA_MULT)  # Red fade
        draw_text("Game Over! You hit the edge.", font, FOOD_COLOR, screen, WIDTH // 2, HEIGHT // 2 - 50, center=True)
        draw_text(f"Final Score: {score}", font, TEXT_COLOR, screen, WIDTH // 2, HEIGHT // 2, center=True)
        draw_text("Press R to Restart", font, FOOD_COLOR, screen, WIDTH // 2, HEIGHT // 2 + 50, center=True)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_r]:
            snake = [(WIDTH // 2, HEIGHT // 2)]
            direction = (0, 0)
            food_pos = random_food_position(snake, [])
            food_type = 'normal'
            score = 0
            game_over = False
            level = 1
            obstacles = []
            powerup_active = False
            FPS = 7

    pygame.display.flip()
    clock.tick(FPS)