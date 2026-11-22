# MinecraftPythonEdition

A Python 3 voxel-engine project targeting Minecraft Java Edition 1.12.2 gameplay/data foundations. The desktop game and multiplayer host are **Python Edition only**; Java Edition clients cannot join the Python Edition LAN server.

## Desktop preview

Install Python 3.12 and dependencies:

```bash
python -m pip install -r requirements.txt
python launcher.py
```

The current desktop preview opens an OpenGL 3.3 window with one generated chunk and a free camera (WASD, Space/Ctrl, Shift, mouse, Escape). Rendering currently uses deterministic placeholder block colors. Texture atlas/resource-pack support, interaction, HUD, inventory, and complete world streaming are still in progress.

## Python Edition LAN host

Use **HOST PYTHON EDITION SERVER** in the launcher to start a Python-only LAN host on port 25575. The current transport supports Python Edition handshake/admission, chat relay, player-state relay, and ping/pong. It is not Minecraft Java protocol 340 and is not yet a complete synchronized multiplayer game.

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
