# Minecraft C++ Native — target 26.3

A C++20 native-port toolchain targeting **Minecraft Java Edition 26.3**. This is not a voxel prototype and does not claim to translate the complete game yet. It is being built as an analyzer, compatibility layer, code generator, and parity-testing system.

## Implemented

- CMake/C++20 project and CLI.
- Bounded JVM class-file parser, including method `Code` attributes and exception tables.
- Constant-pool parsing for standard tags 1, 3–12, and 15–20.
- Class, superclass, interface, field, and method metadata.
- JVM bytecode decoder, including `tableswitch`, `lookupswitch`, and `wide`.
- JVM descriptor parser and control-flow graph builder.
- JVM method descriptor to native C++ signature mapping, including static/instance parameter local-slot layout and category-2 parameters.
- Typed operand-stack verification and definite-initialization analysis for integer locals across reachable control-flow merges.
- Integer bytecode-to-C++ generation for constants, arithmetic, division/remainder, bitwise operations, shifts, local loads/stores, `iinc`, integer conditionals, `goto`, and `ireturn`.
- JVM method-reference and invocation-instruction resolution, including `invokeinterface` descriptor-slot validation.
- Deterministic class/method symbol registry keyed by JVM owner, method name, and full descriptor. A declaration emitter now produces C++ namespace-level prototypes for every method, maps JVM parameter/return descriptors to ABI types, and supplies an explicit receiver pointer for instance methods. Overloaded methods receive distinct stable C++ names; duplicate class and method definitions are rejected. Static-call code generation now uses the same descriptor-aware naming function.
- C++ call-statement generation and a class-aware caller compiler for the exact `invokestatic <method-ref>; ireturn` pattern with static `()I` caller/callee signatures. Calls use the deterministic `mcnative_generated::C_<sanitized-owner>::<method>()` symbol convention; class-level symbol declarations/linking and general method-body integration remain outstanding.
- Local Minecraft 26.3 preparation command: validates the user's official-launcher folder, checks the client JAR size and SHA-1 against the version JSON, writes a local manifest, and extracts only `.class` entries from the verified JAR.
- `inspect-class`, `translate-int`, `translate-method`, `index-classes`, `index-dependencies`, and `prepare` CLI commands. The dependency index resolves `invokevirtual`, `invokespecial`, `invokestatic`, and `invokeinterface` call sites into source/target class and method records.
- Tests and GitHub Actions builds for Linux and Windows.

## Local game preparation

The preparation flow follows the useful part of Horizon's approach: use the player's own installed game, verify the exact pinned inputs, and keep all derived/private files local. It is **not** a Java-to-C++ translator by itself. Horizon's public source describes a from-scratch Rust port plus a preparation tool that imports verified game resources and runs reference-game exporters; it does not simply patch Java bytecode into Rust. This project will build a C++ native implementation and use the local installation as a checked reference/input source.

```bash
mc-native-tool prepare "/path/to/.minecraft" "native-cpp/.local/26.3"
```

The current command verifies the 26.3 client JAR, writes `prepare-manifest.json`, extracts class files into `classes/`, and automatically parses every extracted class into `class-index.csv` (path, internal class name, superclass, class-file version, interfaces, fields, and methods). The ZIP reader supports stored and DEFLATE entries, checks CRC-32, rejects encrypted/ZIP64 entries and unsafe paths, and applies per-class and total extraction limits. It does not extract assets or libraries, and no game binaries are committed to the repository.

## Build

Requirements: CMake 3.24+ and a C++20 compiler.

```bash
cmake -S native-cpp -B build
cmake --build build --config Release
ctest --test-dir build --output-on-failure
```

Generate a declaration-only C++ interface for a parsed JVM class (the generated header contains method prototypes, not method implementations):

```bash
mc-native-tool emit-class path/to/SomeClass.class generated/SomeClass.hpp
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

1. Generate method definitions for supported JVM bodies and connect them to the emitted class declaration interfaces.
2. Extend invocation compilation to primitive arguments and integrate calls into the general method-body compiler.
3. Extend local-variable dataflow to all JVM verification types and category-2 slot rules; then add fields, arrays, and object operations.
4. Exception tables, stack-map verification, class initialization, and Java runtime compatibility.
5. Full JAR/classpath dependency indexing and class hierarchy resolution.
6. Differential testing against the reference JVM, then Minecraft-specific class migration.

## Correctness and game-file policy

- Target version is pinned in `config/target-version.json`; do not silently substitute another Minecraft version.
- The user supplies their own local game installation. Do not commit proprietary game binaries, assets, credentials, or launcher data.
- Unknown features must fail explicitly. Never emit silently incorrect native code.
- The current backend is a narrow integer-method compiler, not a complete JVM and not a playable native Minecraft build. Reflection, dynamic loading, invokedynamic, native methods, concurrency, object identity, exceptions, and Java library behavior still require explicit support.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/CLASS_FILE_PARSER.md](docs/CLASS_FILE_PARSER.md), and [docs/CODE_GENERATION.md](docs/CODE_GENERATION.md).
