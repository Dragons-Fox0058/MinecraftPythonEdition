# First Bytecode-to-C++ Backend

The backend translates a deliberately limited subset of straight-line JVM integer methods. It emits a standalone C++20 function named `translated_method` and uses a `std::uint32_t` operand stack and local-variable array so Java 32-bit integer wraparound is defined rather than relying on C++ signed-overflow behavior.

## Supported opcodes

- `nop`
- `iconst_m1` through `iconst_5`
- `bipush`, `sipush`
- `iload`, `iload_0` through `iload_3`
- `istore`, `istore_0` through `istore_3`
- `iinc`
- `wide iload`, `wide istore`, `wide iinc`
- `iadd`, `isub`, `imul`, `ineg`
- `i2b`, `i2c`, `i2s`
- `ireturn`

For class-file methods, `max_locals` is taken from the method's `Code` attribute. The current `()I` translator initializes local slots to zero, which matches JVM default local state only for slots that are assigned before being read; Java bytecode verification is not implemented yet, so uninitialized reads must be rejected by a future verifier rather than treated as valid source methods.

The backend checks stack depth and local-slot bounds and requires a terminal `ireturn`. Unsupported instructions, branches, calls, fields, object operations, and non-integer returns produce explicit errors.

This is an incremental compiler foundation, not a complete Minecraft class translator. The next expansion is control-flow lowering, typed stack/local verification, exception handling, and runtime object semantics. Each expansion must be differential-tested against a JVM.
