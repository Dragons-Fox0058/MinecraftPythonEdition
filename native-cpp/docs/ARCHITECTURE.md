# Architecture — Minecraft Java 26.3 to native C++

## Pipeline

```text
User's local Minecraft 26.3 installation
                 |
                 v
       Installation Inspector
                 |
                 v
        Artifact / Mapping Index
                 |
                 v
          Java Class Reader
                 |
                 v
       Bytecode + Metadata IR
                 |
          +------+------+
          |             |
          v             v
    C++ Codegen    Compatibility Runtime
          |             |
          +------+------+
                 |
                 v
        Native Modules / Client
                 |
                 v
       Differential Parity Tests
```

## Modules

- **installation-inspector**: validates the selected local installation and records hashes/metadata. It must not download or redistribute proprietary game files.
- **classfile-reader**: parses the JVM class-file format, constant pool, fields, methods, attributes, descriptors, and bytecode.
- **mapping-index**: stores version-specific names and symbol relationships. Missing mappings remain explicitly unresolved.
- **bytecode-ir**: typed instructions, basic blocks, control-flow graph, exception regions, and source provenance.
- **cpp-codegen**: emits C++ only for operations whose semantics are implemented and tested.
- **compat-runtime**: models Java semantics required by generated code: object identity, arrays, integer overflow, floating-point behavior, virtual dispatch, exceptions, and selected standard-library behavior.
- **native-modules**: incrementally replaces or hosts game subsystems behind stable interfaces.
- **parity-runner**: executes the same deterministic test vectors against the reference Java runtime and native implementation.

## Non-negotiable correctness rules

1. Unknown opcodes, attributes, descriptors, or runtime calls must produce actionable diagnostics.
2. Do not silently replace Java behavior with a superficially similar C++ behavior.
3. Preserve integer overflow and signedness rules deliberately.
4. Preserve evaluation order, exceptions, virtual/interface dispatch, and array bounds behavior.
5. Treat reflection, dynamic class loading, invokedynamic, native methods, and concurrency as explicit compatibility work—not as already solved.
6. Every generated method records its original class, method descriptor, input artifact hash, generator version, and support level.
7. Differential tests are required before a translated feature is marked supported.

## Translation strategy

This is a hybrid native-port toolchain, not a promise that arbitrary Java source or bytecode can be converted perfectly by a single text rewrite. The analyzer can inspect the full input; code generation is enabled feature-by-feature as the compatibility runtime grows. Complex JVM facilities may require dedicated native implementations or carefully bounded fallbacks.

## Version policy

The target is pinned to Minecraft Java Edition **26.3** in `config/target-version.json`. Do not substitute 1.12.2 or infer protocol details from another release. Version-specific artifact layouts, mappings, and protocol metadata must be discovered and validated against the user's 26.3 installation.
