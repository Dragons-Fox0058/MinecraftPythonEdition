# MinecraftPythonEdition

A Python 3 voxel-engine project targeting Minecraft Java Edition 1.12.2 behavior and data formats.

## Current engineering status

- Core, block, world, world-generation, entity, and gameplay foundations are implemented with automated unit tests.
- Persistence and protocol-340 networking foundations exist; vanilla-world compatibility and full play-state networking are still in progress.
- Rendering/input/application foundations now include a fixed-step loop, backend-independent input state, and CPU chunk-face meshing.
- This repository is **not yet a complete playable Minecraft client**. The OpenGL window/GPU backend, texture atlas/resource packs, HUD, full network packet integration, and vanilla interoperability verification remain outstanding.

## Tests

Run the current unit suite from the repository root:

```bash
python -m pip install numpy cryptography
python -m unittest discover -s tests -v
```

The GitHub Actions workflow runs this suite on pushes and pull requests.

## Target

Java Edition 1.12.2 (protocol 340). The project aims for interoperability, but compatibility is only claimed for features that have passed real vanilla-server/client or world-fixture tests.
