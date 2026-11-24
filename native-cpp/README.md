# Minecraft C++ Native — target 26.3

A C++20 native-port toolchain targeting **Minecraft Java Edition 26.3**. This is not a voxel prototype and does not claim to translate the complete game yet. It is being built as an analyzer, compatibility layer, code generator, and parity-testing system.

## Implemented

- CMake/C++20 project and CLI.
- Bounded JVM class-file parser.
- Constant-pool parsing for standard tags 1, 3–12, and 15–20.
- Class, superclass, interface, field, and method metadata.
- Method \`Code\` attributes, raw bytecode, and exception tables.
- \`inspect-class\` CLI command.
- Smoke and parser tests.
- Windows/Linux GitHub Actions build workflow.

## Build

Requirements: CMake 3.24+ and a C++20 compiler (MSVC 2022, Clang 16+, or GCC 13+).

\`\`\`bash
cmake -S native-cpp -B build
cmake --build build --config Release
ctest --test-dir build --output-on-failure
\`\`\`

Inspect a class file:

\`\`\`bash
mc-native-tool inspect-class path/to/SomeClass.class
\`\`\`

## Architecture and next milestones

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/CLASS_FILE_PARSER.md](docs/CLASS_FILE_PARSER.md).

Next engineering steps:
1. Constant-pool reference resolver and modified UTF-8 decoder.
2. Bytecode instruction decoder, including \`tableswitch\`, \`lookupswitch\`, and \`wide\`.
3. Control-flow graph and typed intermediate representation.
4. JVM descriptor/signature parser and verifier checks.
5. A deliberately limited, tested bytecode-to-C++ backend.
6. Java-semantics compatibility runtime and differential tests.

## Correctness and game-file policy

- Target version is pinned in \`config/target-version.json\`; do not silently substitute another Minecraft version.
- The user supplies their own local game installation. Do not commit proprietary game binaries, assets, credentials, or launcher data.
- Unknown features must fail explicitly. Never emit silently incorrect native code.
- Automatic class analysis is not the same as full Java-to-C++ conversion. Reflection, dynamic loading, invokedynamic, native methods, concurrency, object identity, exceptions, and Java library behavior require explicit support.
