import math
import os
import random
from dataclasses import dataclass
from pathlib import Path

import pygame


WIDTH, HEIGHT = 960, 600
HALF_HEIGHT = HEIGHT // 2
FPS = 60
FOV = math.radians(66)
HALF_FOV = FOV / 2
NUM_RAYS = 240
MAX_DEPTH = 24
DELTA_ANGLE = FOV / NUM_RAYS
DIST_TO_PLANE = (WIDTH / 2) / math.tan(HALF_FOV)
SCALE = WIDTH // NUM_RAYS
TILE = 64
ASSET_DIR = Path("assets/generated")
ASSET_VERSION = "2"

CURRENT_MAP = []
SOLID_TILES = {"1", "2", "3", "4", "5", "D"}
TEXTURE_TILES = {
    "1": "wall_tech",
    "2": "wall_blood",
    "3": "wall_panel",
    "4": "wall_pipe",
    "5": "wall_altar",
    "D": "door",
}

STORY = [
    "The mining moon Acheron went silent after an illegal drill broke into an old basalt vault.",
    "Your squad is gone. The distress beacon repeats one phrase: DO NOT OPEN THE CORE.",
    "You are the last marine on station. Clear the outpost, seal the rift, and get out alive.",
]


@dataclass
class Enemy:
    x: float
    y: float
    kind: str = "imp"
    health: int = 70
    speed: float = 1.15
    damage: int = 9
    attack_cooldown: float = 0
    pain_timer: float = 0

    @property
    def alive(self):
        return self.health > 0


@dataclass
class Pickup:
    x: float
    y: float
    kind: str
    taken: bool = False


@dataclass
class Level:
    title: str
    briefing: str
    grid: list[str]
    spawn: tuple[float, float, float]
    enemies: list[tuple[float, float, str]]
    pickups: list[tuple[float, float, str]]


class Player:
    def __init__(self):
        self.x = 2.5 * TILE
        self.y = 2.5 * TILE
        self.angle = 0.0
        self.health = 100
        self.ammo = 28
        self.mag = 8
        self.max_mag = 8
        self.reload_timer = 0
        self.shot_timer = 0
        self.damage_flash = 0
        self.bob = 0

    def place(self, spawn):
        sx, sy, angle = spawn
        self.x = sx * TILE
        self.y = sy * TILE
        self.angle = math.radians(angle)
        self.reload_timer = 0
        self.shot_timer = 0
        self.damage_flash = 0


LEVELS = [
    Level(
        "E1M1: Signal Station",
        "The surface comms bunker is crawling with things wearing human shadows. Find the exit lift.",
        [
            "111111111111111",
            "1.............1",
            "1..2....1....X1",
            "1.......1..3..1",
            "1.......1.....1",
            "1..111..D..1111",
            "1.......1.....1",
            "1.3.....1..2..1",
            "1.......1.....1",
            "1...D.........1",
            "1.......2.....1",
            "111111111111111",
        ],
        (2.5, 2.5, 0),
        [(7.5, 2.5, "imp"), (11.5, 3.5, "imp"), (4.5, 8.5, "imp"), (11.5, 9.5, "imp")],
        [(3.5, 3.5, "ammo"), (10.5, 2.5, "health"), (6.5, 8.5, "ammo"), (12.5, 7.5, "health")],
    ),
    Level(
        "E1M2: Waste Cathedral",
        "Below the station, the refinery has become a shrine. The doors open only for the desperate.",
        [
            "111111111111111111",
            "1....4.....1.....X1",
            "1.11.1.111.1.111111",
            "1.1....1.....1....1",
            "1.1.22.1.555.1.2..1",
            "1...2..D.....D....1",
            "111.11111.11111.111",
            "1...1.......1.....1",
            "1.3...11111...3...1",
            "1.....1...1.......1",
            "1..2..1...1..4....1",
            "111111111111111111",
        ],
        (2.5, 9.5, 0),
        [(5.5, 3.5, "crawler"), (9.5, 5.5, "imp"), (13.5, 8.5, "crawler"), (15.5, 10.5, "brute"), (7.5, 9.5, "imp")],
        [(2.5, 7.5, "health"), (4.5, 10.5, "ammo"), (12.5, 4.5, "ammo"), (15.5, 4.5, "health")],
    ),
    Level(
        "E1M3: The Rift Core",
        "The vault heart is awake. Kill the guardian before the rift learns your name.",
        [
            "1111111111111111111",
            "1........4........X1",
            "1.111.1111111.1111.1",
            "1...1.....5.....1..1",
            "111.D.111...111.D.11",
            "1.....1.......1....1",
            "1.222.1..555..1.22.1",
            "1.....D.......D....1",
            "1.333.1..555..1.33.1",
            "1.....1.......1....1",
            "1..1.....4.....1...1",
            "1111111111111111111",
        ],
        (2.5, 10.5, 0),
        [(6.5, 5.5, "crawler"), (12.5, 5.5, "crawler"), (8.5, 8.5, "imp"), (10.5, 8.5, "imp"), (9.5, 6.5, "brute")],
        [(3.5, 1.5, "ammo"), (4.5, 9.5, "health"), (14.5, 9.5, "health"), (15.5, 1.5, "ammo")],
    ),
]

ENEMY_STATS = {
    "imp": {"health": 70, "speed": 1.15, "damage": 9, "sprite": "enemy_imp"},
    "crawler": {"health": 45, "speed": 1.75, "damage": 7, "sprite": "enemy_crawler"},
    "brute": {"health": 165, "speed": 0.82, "damage": 16, "sprite": "enemy_brute"},
}


def clamp(value, low, high):
    return max(low, min(high, value))


def circle(surface, color, pos, radius):
    pygame.draw.circle(surface, color, pos, radius)


def polygon(surface, color, points):
    pygame.draw.polygon(surface, color, points)


def generate_assets():
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    pygame.init()
    random.seed(7)

    def save_wall(name, base, accent, glow=None):
        surf = pygame.Surface((64, 64))
        surf.fill(base)
        for y in range(64):
            tint = int(18 * math.sin(y / 7))
            pygame.draw.line(surf, tuple(clamp(c + tint, 0, 255) for c in base), (0, y), (64, y))
        for x in range(0, 64, 16):
            pygame.draw.line(surf, tuple(max(0, c - 42) for c in base), (x, 0), (x, 64), 2)
        for y in range(0, 64, 16):
            pygame.draw.line(surf, tuple(min(255, c + 24) for c in base), (0, y), (64, y), 1)
        for _ in range(85):
            x, y = random.randrange(64), random.randrange(64)
            shade = random.randint(-34, 32)
            surf.set_at((x, y), tuple(clamp(c + shade, 0, 255) for c in base))
        pygame.draw.rect(surf, accent, (7, 8, 50, 6), border_radius=2)
        pygame.draw.rect(surf, accent, (12, 37, 38, 5), border_radius=2)
        if glow:
            pygame.draw.line(surf, glow, (5, 58), (59, 58), 2)
            pygame.draw.line(surf, glow, (32, 8), (32, 56), 1)
        pygame.image.save(surf, ASSET_DIR / f"{name}.png")

    save_wall("wall_tech", (72, 79, 91), (40, 205, 210), (45, 215, 230))
    save_wall("wall_blood", (88, 37, 39), (214, 32, 37), (240, 58, 42))
    save_wall("wall_panel", (58, 70, 55), (178, 190, 98))
    save_wall("wall_pipe", (45, 52, 58), (111, 146, 156), (65, 190, 190))
    save_wall("wall_altar", (52, 34, 66), (196, 72, 219), (221, 62, 255))
    save_wall("door", (74, 55, 42), (218, 154, 55), (255, 178, 61))

    def save_enemy_imp():
        enemy = pygame.Surface((112, 136), pygame.SRCALPHA)
        pygame.draw.ellipse(enemy, (31, 16, 13, 120), (20, 112, 72, 13))
        pygame.draw.ellipse(enemy, (55, 24, 20), (25, 32, 62, 84))
        circle(enemy, (126, 31, 31), (56, 42), 27)
        circle(enemy, (255, 210, 70), (46, 37), 5)
        circle(enemy, (255, 210, 70), (66, 37), 5)
        pygame.draw.rect(enemy, (34, 17, 16), (41, 55, 31, 7))
        polygon(enemy, (138, 39, 35), [(31, 62), (7, 83), (22, 96), (42, 72)])
        polygon(enemy, (138, 39, 35), [(81, 62), (105, 83), (90, 96), (70, 72)])
        pygame.draw.rect(enemy, (23, 16, 15), (39, 106, 13, 24))
        pygame.draw.rect(enemy, (23, 16, 15), (62, 106, 13, 24))
        pygame.draw.arc(enemy, (238, 84, 54), (24, 21, 64, 54), 0.2, 2.95, 3)
        pygame.image.save(enemy, ASSET_DIR / "enemy_imp.png")
        pain = enemy.copy()
        pain.fill((255, 85, 85, 90), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.image.save(pain, ASSET_DIR / "enemy_imp_pain.png")

    def save_enemy_crawler():
        crawler = pygame.Surface((120, 84), pygame.SRCALPHA)
        pygame.draw.ellipse(crawler, (0, 0, 0, 80), (20, 66, 82, 10))
        pygame.draw.ellipse(crawler, (49, 90, 76), (22, 27, 76, 40))
        for x in (18, 34, 78, 94):
            pygame.draw.line(crawler, (26, 55, 49), (x, 52), (x - 14 if x < 56 else x + 14, 73), 6)
        circle(crawler, (95, 210, 150), (58, 34), 17)
        circle(crawler, (255, 245, 120), (51, 29), 4)
        circle(crawler, (255, 245, 120), (65, 29), 4)
        pygame.draw.arc(crawler, (180, 255, 207), (40, 17, 36, 27), 0.2, 2.9, 2)
        pygame.image.save(crawler, ASSET_DIR / "enemy_crawler.png")
        pain = crawler.copy()
        pain.fill((255, 85, 85, 90), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.image.save(pain, ASSET_DIR / "enemy_crawler_pain.png")

    def save_enemy_brute():
        brute = pygame.Surface((132, 154), pygame.SRCALPHA)
        pygame.draw.ellipse(brute, (0, 0, 0, 90), (25, 134, 82, 12))
        pygame.draw.rect(brute, (65, 50, 75), (32, 48, 68, 76), border_radius=14)
        pygame.draw.rect(brute, (112, 84, 132), (42, 25, 50, 43), border_radius=10)
        circle(brute, (255, 86, 78), (53, 42), 5)
        circle(brute, (255, 86, 78), (79, 42), 5)
        pygame.draw.rect(brute, (28, 20, 36), (49, 59, 36, 8))
        polygon(brute, (92, 70, 112), [(34, 58), (4, 92), (20, 110), (48, 75)])
        polygon(brute, (92, 70, 112), [(98, 58), (128, 92), (112, 110), (84, 75)])
        pygame.draw.rect(brute, (33, 25, 42), (43, 116, 14, 32))
        pygame.draw.rect(brute, (33, 25, 42), (76, 116, 14, 32))
        pygame.draw.line(brute, (225, 96, 245), (35, 88), (98, 88), 3)
        pygame.image.save(brute, ASSET_DIR / "enemy_brute.png")
        pain = brute.copy()
        pain.fill((255, 85, 85, 90), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.image.save(pain, ASSET_DIR / "enemy_brute_pain.png")

    save_enemy_imp()
    save_enemy_crawler()
    save_enemy_brute()

    pistol = pygame.Surface((320, 230), pygame.SRCALPHA)
    pygame.draw.rect(pistol, (18, 18, 22), (146, 68, 58, 128), border_radius=9)
    pygame.draw.rect(pistol, (66, 72, 84), (122, 28, 112, 78), border_radius=10)
    pygame.draw.rect(pistol, (20, 20, 24), (145, 15, 66, 29), border_radius=5)
    pygame.draw.rect(pistol, (140, 146, 158), (130, 38, 93, 13))
    pygame.draw.rect(pistol, (12, 12, 17), (152, 153, 45, 59), border_radius=7)
    pygame.draw.circle(pistol, (235, 176, 65), (179, 25), 10)
    pygame.draw.line(pistol, (95, 205, 225), (132, 92), (228, 92), 2)
    pygame.image.save(pistol, ASSET_DIR / "weapon_pistol.png")

    muzzle = pygame.Surface((320, 230), pygame.SRCALPHA)
    polygon(muzzle, (255, 246, 137, 235), [(170, 0), (138, 45), (177, 31), (213, 52), (194, 15)])
    polygon(muzzle, (255, 113, 42, 210), [(175, 0), (156, 42), (197, 39)])
    muzzle.blit(pistol, (0, 0))
    pygame.image.save(muzzle, ASSET_DIR / "weapon_pistol_fire.png")

    for name, color in [("ammo", (230, 186, 73)), ("health", (219, 45, 54))]:
        surf = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (0, 0, 0, 80), (9, 46, 46, 10))
        pygame.draw.rect(surf, color, (14, 18, 36, 30), border_radius=6)
        pygame.draw.rect(surf, tuple(clamp(c + 35, 0, 255) for c in color), (18, 21, 28, 5), border_radius=2)
        if name == "health":
            pygame.draw.rect(surf, (250, 240, 240), (28, 22, 8, 22))
            pygame.draw.rect(surf, (250, 240, 240), (21, 29, 22, 8))
        else:
            for x in (20, 30, 40):
                pygame.draw.rect(surf, (95, 68, 34), (x, 12, 7, 34), border_radius=3)
        pygame.image.save(surf, ASSET_DIR / f"pickup_{name}.png")

    with open(ASSET_DIR / "version.txt", "w", encoding="utf-8") as handle:
        handle.write(ASSET_VERSION)


def load_assets():
    version_file = ASSET_DIR / "version.txt"
    if not version_file.exists() or version_file.read_text(encoding="utf-8").strip() != ASSET_VERSION:
        generate_assets()
    textures = {
        name: pygame.image.load(ASSET_DIR / f"{name}.png").convert()
        for name in ["wall_tech", "wall_blood", "wall_panel", "wall_pipe", "wall_altar", "door"]
    }
    assets = {
        "textures": textures,
        "weapon": pygame.image.load(ASSET_DIR / "weapon_pistol.png").convert_alpha(),
        "weapon_fire": pygame.image.load(ASSET_DIR / "weapon_pistol_fire.png").convert_alpha(),
        "pickup_ammo": pygame.image.load(ASSET_DIR / "pickup_ammo.png").convert_alpha(),
        "pickup_health": pygame.image.load(ASSET_DIR / "pickup_health.png").convert_alpha(),
    }
    for kind in ENEMY_STATS:
        assets[f"enemy_{kind}"] = pygame.image.load(ASSET_DIR / f"enemy_{kind}.png").convert_alpha()
        assets[f"enemy_{kind}_pain"] = pygame.image.load(ASSET_DIR / f"enemy_{kind}_pain.png").convert_alpha()
    return assets


def tile_at(px, py):
    mx, my = int(px // TILE), int(py // TILE)
    if my < 0 or my >= len(CURRENT_MAP) or mx < 0 or mx >= len(CURRENT_MAP[0]):
        return "1"
    return CURRENT_MAP[my][mx]


def is_blocked(px, py):
    return tile_at(px, py) in SOLID_TILES


def has_line_of_sight(x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    steps = int(max(abs(dx), abs(dy)) / 10) + 1
    for i in range(steps):
        t = i / steps
        if is_blocked(x1 + dx * t, y1 + dy * t):
            return False
    return True


def has_enemy_line_of_sight(player, enemy):
    dx, dy = enemy.x - player.x, enemy.y - player.y
    dist = math.hypot(dx, dy)
    if dist <= 1:
        return True
    side_x = -dy / dist
    side_y = dx / dist
    # Test a few points across the body so enemies visible around door frames
    # and corners can still be shot.
    for offset in (0, -18, 18, -30, 30):
        tx = enemy.x + side_x * offset
        ty = enemy.y + side_y * offset
        if not is_blocked(tx, ty) and has_line_of_sight(player.x, player.y, tx, ty):
            return True
    return False


def normalize_angle(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


def cast_ray(px, py, angle):
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)
    depth = 1.0
    hit = "1"
    texture_x = 0
    vertical = False
    while depth < MAX_DEPTH * TILE:
        x = px + cos_a * depth
        y = py + sin_a * depth
        hit = tile_at(x, y)
        if hit in SOLID_TILES:
            vertical = int((x - cos_a * 2) // TILE) != int(x // TILE)
            texture_x = int(y % TILE if vertical else x % TILE)
            break
        depth += 3.0
    return depth, hit, texture_x, vertical


def cast_scene(screen, player, assets, level_index):
    zbuffer = []
    palettes = [
        ((14, 18, 31), (63, 56, 64), (36, 33, 29)),
        ((17, 12, 24), (71, 41, 49), (30, 26, 25)),
        ((13, 10, 25), (42, 25, 70), (26, 23, 31)),
    ]
    sky_top, sky_bottom, floor = palettes[level_index % len(palettes)]
    for y in range(HALF_HEIGHT):
        blend = y / HALF_HEIGHT
        color = tuple(int(sky_top[i] * (1 - blend) + sky_bottom[i] * blend) for i in range(3))
        pygame.draw.line(screen, color, (0, y), (WIDTH, y))
    pygame.draw.rect(screen, floor, (0, HALF_HEIGHT, WIDTH, HALF_HEIGHT))
    for y in range(HALF_HEIGHT, HEIGHT, 4):
        shade = clamp(62 - (y - HALF_HEIGHT) // 9, 18, 62)
        pygame.draw.line(screen, (shade, max(0, shade - 7), max(0, shade - 11)), (0, y), (WIDTH, y + 3))

    ray_angle = player.angle - HALF_FOV
    for ray in range(NUM_RAYS):
        depth, hit, tex_x, vertical = cast_ray(player.x, player.y, ray_angle)
        corrected = depth * math.cos(player.angle - ray_angle)
        zbuffer.append(corrected)
        proj_height = min(int((TILE / max(corrected, 0.1)) * DIST_TO_PLANE), HEIGHT * 2)
        texture = assets["textures"][TEXTURE_TILES.get(hit, "wall_tech")]
        column = texture.subsurface((tex_x, 0, 1, TILE))
        column = pygame.transform.scale(column, (SCALE + 1, proj_height))
        shade = clamp(255 - int(corrected * 0.27), 38, 255)
        if not vertical:
            shade = int(shade * 0.78)
        column.fill((shade, shade, shade), special_flags=pygame.BLEND_MULT)
        screen.blit(column, (ray * SCALE, HALF_HEIGHT - proj_height // 2))
        ray_angle += DELTA_ANGLE
    return zbuffer


def resolve_move(entity, dx, dy, radius=16):
    if not is_blocked(entity.x + dx + math.copysign(radius, dx or 1), entity.y):
        entity.x += dx
    if not is_blocked(entity.x, entity.y + dy + math.copysign(radius, dy or 1)):
        entity.y += dy


def update_player(player, pickups, dt):
    keys = pygame.key.get_pressed()
    mouse_dx, _ = pygame.mouse.get_rel()
    player.angle += mouse_dx * 0.0027
    rot_speed = 2.35 * dt
    if keys[pygame.K_LEFT]:
        player.angle -= rot_speed
    if keys[pygame.K_RIGHT]:
        player.angle += rot_speed

    speed = 165 * dt
    dx = dy = 0
    forward = int(keys[pygame.K_w] or keys[pygame.K_UP]) - int(keys[pygame.K_s] or keys[pygame.K_DOWN])
    strafe = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
    if forward or strafe:
        dx += math.cos(player.angle) * forward * speed
        dy += math.sin(player.angle) * forward * speed
        dx += math.cos(player.angle + math.pi / 2) * strafe * speed
        dy += math.sin(player.angle + math.pi / 2) * strafe * speed
        player.bob += dt * 10
    resolve_move(player, dx, dy, 15)
    player.angle %= math.tau

    if player.reload_timer > 0:
        player.reload_timer -= dt
        if player.reload_timer <= 0:
            need = player.max_mag - player.mag
            take = min(need, player.ammo)
            player.mag += take
            player.ammo -= take
    if player.shot_timer > 0:
        player.shot_timer -= dt
    if player.damage_flash > 0:
        player.damage_flash -= dt

    for pickup in pickups:
        if pickup.taken:
            continue
        if math.hypot(pickup.x - player.x, pickup.y - player.y) < 34:
            pickup.taken = True
            if pickup.kind == "health":
                player.health = min(100, player.health + 30)
            else:
                player.ammo += 12


def shoot(player, enemies, zbuffer=None):
    if player.reload_timer > 0 or player.shot_timer > 0 or player.mag <= 0:
        return
    player.mag -= 1
    player.shot_timer = 0.18
    best = None
    best_dist = 999999
    alive_count = sum(1 for enemy in enemies if enemy.alive)
    for enemy in enemies:
        if not enemy.alive:
            continue
        dx, dy = enemy.x - player.x, enemy.y - player.y
        dist = math.hypot(dx, dy)
        angle_to = math.atan2(dy, dx)
        diff = abs(normalize_angle(angle_to - player.angle))
        hit_width = max(math.atan2(44 if enemy.kind == "brute" else 34, dist), 0.055)
        if diff >= hit_width or dist >= best_dist:
            continue
        exposed = has_enemy_line_of_sight(player, enemy)
        if zbuffer:
            screen_x = WIDTH // 2 + math.tan(normalize_angle(angle_to - player.angle)) * DIST_TO_PLANE
            ray_index = int(screen_x / SCALE)
            if 0 <= ray_index < len(zbuffer) and dist <= zbuffer[ray_index] + 44:
                exposed = True
        if alive_count == 1 and diff < 0.22:
            exposed = True
        if exposed:
            best = enemy
            best_dist = dist
    if best:
        best.health -= 36
        best.pain_timer = 0.16


def update_enemies(player, enemies, dt):
    for enemy in enemies:
        if not enemy.alive:
            continue
        if enemy.pain_timer > 0:
            enemy.pain_timer -= dt
        if enemy.attack_cooldown > 0:
            enemy.attack_cooldown -= dt
        dx, dy = player.x - enemy.x, player.y - enemy.y
        dist = math.hypot(dx, dy)
        if dist < 560 and has_line_of_sight(enemy.x, enemy.y, player.x, player.y):
            if dist > 54:
                step = enemy.speed * 64 * dt
                resolve_move(enemy, dx / dist * step, dy / dist * step, 17)
            elif enemy.attack_cooldown <= 0:
                player.health -= random.randint(max(3, enemy.damage - 3), enemy.damage + 4)
                player.damage_flash = 0.18
                enemy.attack_cooldown = 0.86


def draw_billboards(screen, player, enemies, pickups, zbuffer, assets):
    sprites = []
    for enemy in enemies:
        if enemy.alive:
            suffix = "_pain" if enemy.pain_timer > 0 else ""
            sprites.append((enemy.x, enemy.y, f"enemy_{enemy.kind}{suffix}", 1.58 if enemy.kind == "brute" else 1.25))
    for pickup in pickups:
        if not pickup.taken:
            sprites.append((pickup.x, pickup.y, f"pickup_{pickup.kind}", 0.58))
    sprites.sort(key=lambda s: math.hypot(s[0] - player.x, s[1] - player.y), reverse=True)
    for sx, sy, key, size_factor in sprites:
        dx, dy = sx - player.x, sy - player.y
        distance = math.hypot(dx, dy)
        theta = math.atan2(dy, dx)
        gamma = normalize_angle(theta - player.angle)
        if abs(gamma) > HALF_FOV + 0.35:
            continue
        screen_x = WIDTH // 2 + math.tan(gamma) * DIST_TO_PLANE
        sprite = assets[key]
        size = int((TILE * size_factor / max(distance * math.cos(gamma), 1)) * DIST_TO_PLANE)
        if size <= 2:
            continue
        ray_index = int(screen_x / SCALE)
        if 0 <= ray_index < len(zbuffer) and distance > zbuffer[ray_index] + 38:
            continue
        sprite_scaled = pygame.transform.scale(sprite, (size, int(size * sprite.get_height() / sprite.get_width())))
        x = int(screen_x - sprite_scaled.get_width() / 2)
        y = int(HALF_HEIGHT - sprite_scaled.get_height() / 2 + size * 0.18)
        fog = clamp(255 - int(distance * 0.15), 78, 255)
        sprite_scaled.fill((fog, fog, fog, 255), special_flags=pygame.BLEND_MULT)
        screen.blit(sprite_scaled, (x, y))


def draw_weapon(screen, player, assets):
    firing = player.shot_timer > 0.1
    weapon = assets["weapon_fire" if firing else "weapon"]
    bob = int(math.sin(player.bob) * 5) if player.bob else 0
    if player.reload_timer > 0:
        bob += int(34 * math.sin((1 - player.reload_timer / 0.75) * math.pi))
    x = WIDTH // 2 - weapon.get_width() // 2
    y = HEIGHT - weapon.get_height() + 22 + bob
    screen.blit(weapon, (x, y))


def draw_hud(screen, player, enemies, font, small_font, show_minimap, level):
    hud = pygame.Surface((WIDTH, 62), pygame.SRCALPHA)
    hud.fill((0, 0, 0, 150))
    screen.blit(hud, (0, HEIGHT - 62))
    health_color = (230, 52, 61) if player.health < 35 else (232, 220, 192)
    screen.blit(font.render(f"HEALTH {max(player.health, 0)}", True, health_color), (20, HEIGHT - 47))
    screen.blit(font.render(f"AMMO {player.mag}/{player.ammo}", True, (232, 220, 192)), (220, HEIGHT - 47))
    alive = sum(1 for e in enemies if e.alive)
    screen.blit(font.render(f"HOSTILES {alive}", True, (232, 220, 192)), (420, HEIGHT - 47))
    if alive == 0:
        objective = "Find the exit"
    elif alive == 1:
        last = next(e for e in enemies if e.alive)
        direction = math.degrees(normalize_angle(math.atan2(last.y - player.y, last.x - player.x) - player.angle))
        side = "ahead" if abs(direction) < 25 else ("right" if direction > 0 else "left")
        objective = f"Last hostile is {side}"
    else:
        objective = "Clear hostiles"
    screen.blit(small_font.render(f"{level.title} | {objective}", True, (176, 178, 165)), (20, HEIGHT - 22))
    if player.reload_timer > 0:
        text = font.render("RELOADING", True, (255, 218, 90))
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT - 96))
    if show_minimap:
        draw_minimap(screen, player, enemies)
    hint = small_font.render("E doors | M map | R reload", True, (170, 166, 150))
    screen.blit(hint, (WIDTH - hint.get_width() - 14, HEIGHT - 24))


def draw_minimap(screen, player, enemies):
    scale = 7
    ox, oy = 14, 14
    pygame.draw.rect(screen, (0, 0, 0), (ox - 5, oy - 5, len(CURRENT_MAP[0]) * scale + 10, len(CURRENT_MAP) * scale + 10))
    for y, row in enumerate(CURRENT_MAP):
        for x, tile in enumerate(row):
            if tile in SOLID_TILES:
                color = (93, 93, 96) if tile != "D" else (138, 88, 42)
                pygame.draw.rect(screen, color, (ox + x * scale, oy + y * scale, scale, scale))
            elif tile == "X":
                pygame.draw.rect(screen, (80, 210, 125), (ox + x * scale, oy + y * scale, scale, scale))
    px, py = int(ox + player.x / TILE * scale), int(oy + player.y / TILE * scale)
    circle(screen, (70, 210, 255), (px, py), 3)
    pygame.draw.line(screen, (70, 210, 255), (px, py), (px + math.cos(player.angle) * 10, py + math.sin(player.angle) * 10), 2)
    for enemy in enemies:
        if enemy.alive:
            circle(screen, (224, 46, 48), (int(ox + enemy.x / TILE * scale), int(oy + enemy.y / TILE * scale)), 3)


def open_nearby_door(player):
    global CURRENT_MAP
    new_rows = []
    changed = False
    for y, row in enumerate(CURRENT_MAP):
        chars = list(row)
        for x, tile in enumerate(chars):
            if tile == "D":
                cx, cy = (x + 0.5) * TILE, (y + 0.5) * TILE
                if math.hypot(cx - player.x, cy - player.y) < 88:
                    chars[x] = "."
                    changed = True
        new_rows.append("".join(chars))
    if changed:
        CURRENT_MAP = new_rows


def make_world(level, player, keep_stats=False):
    global CURRENT_MAP
    CURRENT_MAP = list(level.grid)
    old_health, old_ammo = player.health, player.ammo
    player.place(level.spawn)
    if not keep_stats:
        player.health = 100
        player.ammo = 28
        player.mag = player.max_mag
    else:
        player.health = min(100, old_health + 25)
        player.ammo = old_ammo + 10
        player.mag = player.max_mag
    enemies = []
    for ex, ey, kind in level.enemies:
        stats = ENEMY_STATS[kind]
        enemies.append(Enemy(ex * TILE, ey * TILE, kind, stats["health"], stats["speed"], stats["damage"]))
    pickups = [Pickup(px * TILE, py * TILE, kind) for px, py, kind in level.pickups]
    return enemies, pickups


def draw_panel(screen, title, lines, font, small_font, footer="Press Enter"):
    screen.fill((8, 9, 14))
    for y in range(0, HEIGHT, 5):
        shade = 16 + int(15 * math.sin(y * 0.025))
        pygame.draw.line(screen, (shade, shade, shade + 8), (0, y), (WIDTH, y))
    pygame.draw.rect(screen, (20, 23, 34), (105, 90, WIDTH - 210, HEIGHT - 180), border_radius=14)
    pygame.draw.rect(screen, (78, 190, 205), (105, 90, WIDTH - 210, HEIGHT - 180), 2, border_radius=14)
    title_surf = font.render(title, True, (235, 224, 190))
    screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, 130))
    y = 205
    for line in lines:
        surf = small_font.render(line, True, (202, 205, 190))
        screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, y))
        y += 30
    footer_surf = small_font.render(footer, True, (98, 230, 240))
    screen.blit(footer_surf, (WIDTH // 2 - footer_surf.get_width() // 2, HEIGHT - 135))


def draw_menu(screen, font, small_font, selected):
    options = ["Start Campaign", "Controls", "Quit"]
    draw_panel(screen, "RIFTBREAKER", STORY, font, small_font, "Arrow keys/WASD to choose, Enter to select")
    for i, option in enumerate(options):
        color = (255, 222, 95) if i == selected else (210, 211, 198)
        label = f"> {option} <" if i == selected else option
        surf = font.render(label, True, color)
        screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, 365 + i * 42))


def player_on_exit(player):
    return tile_at(player.x, player.y) == "X"


def main():
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
    pygame.init()
    pygame.display.set_caption("Riftbreaker - Pygame Raycasting FPS")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    assets = load_assets()
    font = pygame.font.Font(None, 38)
    big_font = pygame.font.Font(None, 72)
    small_font = pygame.font.Font(None, 24)
    player = Player()
    level_index = 0
    enemies, pickups = make_world(LEVELS[level_index], player)
    show_minimap = True
    state = "menu"
    menu_selected = 0
    mouse_locked = False
    zbuffer = None

    def set_mouse_lock(locked):
        nonlocal mouse_locked
        if mouse_locked == locked:
            return
        pygame.mouse.set_visible(not locked)
        pygame.event.set_grab(locked)
        pygame.mouse.get_rel()
        mouse_locked = locked

    while True:
        dt = clock.tick(FPS) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            if state == "menu":
                set_mouse_lock(False)
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        menu_selected = (menu_selected - 1) % 3
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        menu_selected = (menu_selected + 1) % 3
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if menu_selected == 0:
                            level_index = 0
                            enemies, pickups = make_world(LEVELS[level_index], player)
                            state = "briefing"
                        elif menu_selected == 1:
                            state = "controls"
                        else:
                            pygame.quit()
                            return
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        return
                continue

            if state in {"briefing", "controls", "level_clear", "victory", "dead"}:
                set_mouse_lock(False)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        state = "menu"
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if state == "briefing":
                            state = "playing"
                        elif state == "controls":
                            state = "menu"
                        elif state == "level_clear":
                            level_index += 1
                            if level_index >= len(LEVELS):
                                state = "victory"
                            else:
                                enemies, pickups = make_world(LEVELS[level_index], player, keep_stats=True)
                                state = "briefing"
                        elif state in {"victory", "dead"}:
                            state = "menu"
                continue

            if state == "playing":
                set_mouse_lock(True)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        state = "menu"
                    if event.key == pygame.K_m:
                        show_minimap = not show_minimap
                    if event.key == pygame.K_e:
                        open_nearby_door(player)
                    if event.key == pygame.K_r and player.mag < player.max_mag and player.ammo > 0:
                        player.reload_timer = 0.75
                    if event.key == pygame.K_SPACE:
                        shoot(player, enemies, zbuffer)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    shoot(player, enemies, zbuffer)

        if state == "menu":
            draw_menu(screen, big_font, small_font, menu_selected)
        elif state == "controls":
            draw_panel(
                screen,
                "CONTROLS",
                [
                    "WASD / arrows: move and strafe",
                    "Mouse / left-right arrows: look",
                    "Space / left mouse: shoot",
                    "R: reload    E: open doors    M: minimap",
                    "Clear all enemies, then step into the green exit tile.",
                ],
                font,
                small_font,
                "Press Enter to return",
            )
        elif state == "briefing":
            draw_panel(screen, LEVELS[level_index].title, [LEVELS[level_index].briefing], font, small_font, "Press Enter to deploy")
        elif state == "level_clear":
            draw_panel(screen, "AREA CLEAR", ["The lift groans open. Something below screams back."], font, small_font, "Press Enter for next level")
        elif state == "victory":
            draw_panel(screen, "RIFT SEALED", ["The core collapses into silence.", "Acheron will not remember your name, but it will survive."], font, small_font, "Press Enter for menu")
        elif state == "dead":
            draw_panel(screen, "YOU DIED", ["The station keeps your signal.", "The rift keeps the rest."], font, small_font, "Press Enter for menu")
        elif state == "playing":
            if player.mag == 0 and player.ammo > 0 and player.reload_timer <= 0:
                player.reload_timer = 0.75
            update_player(player, pickups, dt)
            update_enemies(player, enemies, dt)
            if player.health <= 0:
                state = "dead"
            elif all(not e.alive for e in enemies) and player_on_exit(player):
                state = "level_clear"

            zbuffer = cast_scene(screen, player, assets, level_index)
            draw_billboards(screen, player, enemies, pickups, zbuffer, assets)
            draw_weapon(screen, player, assets)
            draw_hud(screen, player, enemies, font, small_font, show_minimap, LEVELS[level_index])
            if all(not e.alive for e in enemies):
                text = font.render("EXIT UNLOCKED", True, (110, 235, 125))
                screen.blit(text, (WIDTH // 2 - text.get_width() // 2, 82))
            if player.damage_flash > 0:
                flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                flash.fill((255, 0, 0, int(120 * player.damage_flash / 0.18)))
                screen.blit(flash, (0, 0))

        pygame.display.flip()


if __name__ == "__main__":
    main()
