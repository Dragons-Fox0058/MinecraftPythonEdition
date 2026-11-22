# MinecraftPythonEdition

A Python 3 voxel-engine project targeting Minecraft Java Edition 1.12.2 gameplay/data foundations. The desktop game and multiplayer host are **Python Edition only**; Java Edition clients cannot join the Python Edition LAN server.

## Single-player desktop build

Install Python 3.12 and dependencies:

```bash
python -m pip install -r requirements.txt
python launcher.py
```

The launcher lets you enter a world name and seed, then opens a GLFW/OpenGL 3.3 first-person session. Worlds are stored under `saves/<world name>/` in Anvil/NBT form and saved when the game window closes. The renderer keeps a 5×5 chunk area around the player.

### Current controls

- **W/A/S/D:** move
- **Space:** jump
- **Shift:** sprint
- **Mouse:** look around
- **Left mouse:** mine the targeted block
- **Right mouse:** place the selected block
- **1–9:** choose a temporary block palette slot
- **Escape:** close the game and save the world
- **F6/F7:** start/stop a Python Edition host or connect to one

Mining produces item entities for the supported block subset; collected items enter the 36-slot inventory, and placement consumes the selected stack. The player has health and hunger state, and the renderer draws a basic crosshair, nine-slot hotbar frame, and health/hunger bars. The item catalogue is still a small local subset rather than the complete verified 1.12.2 catalogue. Placeholder block colors remain; the vanilla texture atlas, item icons/count text, inventory screen, crafting UI, pause/settings menus, mob simulation, and richer Survival mechanics are not complete. GPU/Windows desktop smoke testing is also outstanding.

## Python Edition LAN host

Use **HOST PYTHON EDITION SERVER** in the launcher to start a Python-only LAN host on port 25575. The in-game preview exposes F6 to host and F7 to join. The transport supports Python Edition handshake/admission, chat relay, player-state relay, and ping/pong. It is not Minecraft Java protocol 340 and is not yet a complete synchronized multiplayer game.

## Windows launcher EXE

On Windows 10/11 with Python 3.12 installed, run:

```bat
build_windows.bat
```

The build creates `dist\\MinecraftPythonLauncher.exe`. GitHub Actions also has a Windows build workflow that publishes the executable as a downloadable workflow artifact when it succeeds.

## Tests

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

The automated tests are not a substitute for desktop GPU smoke testing or genuine Minecraft 1.12.2 world/server compatibility fixtures.

## Target and compatibility

- World format target: Java Edition 1.12.2 Anvil/NBT.
- Existing network client target: Java Edition protocol 340, with incomplete Play packet coverage.
- New LAN host: Python Edition custom protocol only.
- Java Edition client/server interoperability is not claimed unless verified by dedicated integration tests.
