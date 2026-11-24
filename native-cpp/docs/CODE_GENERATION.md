# First Bytecode-to-C++ Backend

The initial backend intentionally translates only straight-line JVM integer methods. It emits a standalone C++20 function named \`translated_method\` and uses a \`std::uint32_t\` operand stack so Java 32-bit integer wraparound is defined rather than relying on C++ signed-overflow behavior.

## Supported opcodes

- \`nop\`
- \`iconst_m1\` through \`iconst_5\`
- \`bipush\`, \`sipush\`
- \`iadd\`, \`isub\`, \`imul\`, \`ineg\`
- \`i2b\`, \`i2c\`, \`i2s\`
- \`ireturn\`

The backend checks operand-stack depth and requires a terminal \`ireturn\`. Unsupported instructions, branches, locals, calls, fields, object operations, and non-integer returns produce explicit errors.

This is a proof-of-pipeline subset, not a Minecraft class translator. The next expansion requires local-variable support, branch/control-flow lowering, typed stack analysis, exception handling, and runtime object semantics. Each expansion must be differential-tested against a JVM.
