# Minecraft C++ Native — target 26.3

This directory is a separate C++20 workstream for a native compatibility/translation project targeting **Minecraft Java Edition 26.3**.

The goal is not to build a small voxel prototype. The goal is to build tooling that can inspect a user's locally installed game version, analyze Java class files and metadata, produce a native C++ representation where semantics can be preserved, and verify behavior against the reference Java runtime.

## Current status

This is the initial project scaffold. It does **not** yet translate Minecraft or produce a playable native client.

## Principles

- Keep the existing Python project and its history untouched.
- Never assume that Java bytecode can be mechanically translated to equivalent C++ without a compatibility runtime.
- Separate bytecode analysis, intermediate representation (IR), code generation, runtime compatibility, native engine integration, and parity testing.
- Treat Minecraft 26.3 as the target version. Do not silently substitute an older version.
- Read game files from a user-provided local installation. Do not commit proprietary game binaries, assets, credentials, or launcher data.
- Generated output must be reproducible and traceable to source class/method metadata.

## Build

Requirements: CMake 3.24+ and a C++20 compiler (MSVC 2022, Clang 16+, or GCC 13+).

```bash
cmake -S . -B build
cmake --build build --config Release
ctest --test-dir build --output-on-failure
```

## Initial milestone

1. Build a class-file reader for Java 26.3's locally installed client/server artifacts.
2. Extract class, field, method, descriptor, constant-pool, and bytecode metadata.
3. Build a typed, control-flow-aware IR.
4. Implement a small, testable bytecode-to-C++ subset.
5. Add a compatibility runtime for Java object, array, exception, numeric, and method-dispatch semantics.
6. Differential-test supported operations against the reference Java runtime.

Unsupported bytecode or runtime features must fail explicitly; never emit silently incorrect C++.
