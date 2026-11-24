# Minecraft C++ Native — target 26.3

A C++20 native-port toolchain targeting **Minecraft Java Edition 26.3**. This is not a voxel prototype and does not claim to translate the complete game yet. It is being built as an analyzer, compatibility layer, code generator, and parity-testing system.

## Implemented

- CMake/C++20 project and CLI.
- Bounded JVM class-file parser, including method `Code` attributes and exception tables.
- Constant-pool parsing for standard tags 1, 3–12, and 15–20.
- Class, superclass, interface, field, and method metadata.
- JVM bytecode decoder, including `tableswitch`, `lookupswitch`, and `wide`.
- JVM descriptor parser and control-flow graph builder.
- Typed operand-stack verification and definite-initialization analysis for integer locals across reachable control-flow merges.
- Integer bytecode-to-C++ generation for constants, arithmetic, division/remainder, bitwise operations, shifts, local loads/stores, `iinc`, integer conditionals, `goto`, and `ireturn`.
- `inspect-class`, `translate-int`, `translate-method`, and `index-classes` CLI commands.
- Tests and GitHub Actions builds for Linux and Windows.

## Build

Requirements: CMake 3.24+ and a C++20 compiler.

```bash
cmake -S native-cpp -B build
cmake --build build --config Release
ctest --test-dir build --output-on-failure
```

Inspect and translate a class method:

```bash
mc-native-tool inspect-class path/to/SomeClass.class
mc-native-tool translate-method path/to/SomeClass.class methodName "()I"
```

Index an extracted class directory:

```bash
mc-native-tool index-classes path/to/extracted/classes classes.csv
```

## Next engineering milestones

1. Constant-pool reference resolution and modified UTF-8 decoding.
2. Extend local-variable dataflow to all JVM verification types and category-2 slot rules.
3. Method arguments, fields, invocation semantics, arrays, and object operations.
4. Exception tables, stack-map verification, class initialization, and Java runtime compatibility.
5. JAR ingestion and full classpath dependency resolution.
6. Differential testing against the reference JVM, then Minecraft-specific class migration.

## Correctness and game-file policy

- Target version is pinned in `config/target-version.json`; do not silently substitute another Minecraft version.
- The user supplies their own local game installation. Do not commit proprietary game binaries, assets, credentials, or launcher data.
- Unknown features must fail explicitly. Never emit silently incorrect native code.
- The current backend is a narrow integer-method compiler, not a complete JVM and not a playable native Minecraft build. Reflection, dynamic loading, invokedynamic, native methods, concurrency, object identity, exceptions, and Java library behavior still require explicit support.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/CLASS_FILE_PARSER.md](docs/CLASS_FILE_PARSER.md), and [docs/CODE_GENERATION.md](docs/CODE_GENERATION.md).
