# First Bytecode-to-C++ Backend

The backend translates a limited subset of JVM integer methods into a standalone C++20 function named `translated_method`. It uses `std::uint32_t` for JVM int values so 32-bit wraparound is defined instead of relying on C++ signed-overflow behavior.

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
- `ifeq`, `ifne`, `iflt`, `ifge`, `ifgt`, `ifle`
- `if_icmpeq`, `if_icmpne`, `if_icmplt`, `if_icmpge`, `if_icmpgt`, `if_icmple`
- `goto`, `goto_w`
- `ireturn`

Branches are emitted as C++ labels and jumps. Before code generation, the control-flow graph builder validates branch destinations and instruction boundaries. Operand-stack underflow and uninitialized local reads are guarded in the generated function at runtime. For class-file methods, `max_locals` is taken from the method's `Code` attribute.

## Current limitations

This is not a complete JVM implementation or a Minecraft class translator. The backend currently handles only integer operations and straight-line/branching control flow in this subset. It does not yet implement verifier dataflow across branch merges, method arguments, long/float/double values, calls, fields, arrays, objects, exceptions, monitors, class initialization, or JVM runtime semantics. Methods with unsupported instructions fail explicitly.

The next expansion requires typed stack/local verification, invocation and field semantics, exception handling, and a compatible runtime layer. Every expansion must be differential-tested against a JVM.
