# Pygame Doom-Style Raycasting FPS

A compact Doom-inspired FPS built with Pygame. It uses a classic 2.5D raycasting renderer, generated pixel-art sprites, billboard enemies, shooting, enemy AI, pickups, doors, a minimap, story screens, and a small three-level campaign.

## Run

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

The first launch generates PNG assets in `assets/generated/`. The art is original/generated so the project stays safe from copyrighted Doom asset issues.

If you are on Python 3.14, this project uses `pygame-ce` because the classic `pygame` package may not provide a prebuilt wheel yet. `pygame-ce` is imported the same way in code: `import pygame`.

## Controls

- `WASD` or arrow keys: move and strafe
- Mouse or `Left/Right`: look
- `Space` or left mouse: shoot
- `R`: reload
- `E`: open nearby doors
- `M`: toggle minimap
- `Esc`: quit

## Campaign

- Title menu with start, controls, and quit options
- Story briefing before each mission
- Three levels with different layouts and enemy mixes
- Clear all enemies, then step into the green exit tile to advance
- Victory and death screens

## Notes

This is intentionally a small, hackable starter project. The sprites and textures are generated procedurally by `main.py`, so you can edit the drawing functions and rerun the game to refresh the art.

If you want to use internet assets later, prefer free assets with clear licenses such as CC0 or CC-BY, and keep attribution notes in the repo.
