# Bytecode and Descriptor Analysis

## Bytecode decoder

The instruction decoder converts a Code attribute's byte array into offset-preserving instruction records. It handles fixed-width operands, branch operands, constant-pool operands, and the variable-length \`tableswitch\`, \`lookupswitch\`, and \`wide\` forms. Each record retains raw operand bytes and the next instruction offset.

The decoder rejects truncated instructions, invalid switch bounds, negative lookup pair counts, illegal \`wide\` sub-opcodes, and reserved opcodes. It does not yet resolve branch targets, constant-pool operands, stack effects, or verify control flow.

## Control-flow graph

The CFG builder identifies basic-block leaders, validates that branch targets land on instruction boundaries, and creates successor edges for conditional/unconditional branches, switch instructions, fallthrough, returns, and throws. Legacy `jsr`/ `ret` subroutine semantics are represented only conservatively; `ret` has no statically resolved successor. This graph is a structural foundation, not yet a verifier or optimizer.

## Descriptor parser

Field and method descriptor parsing supports primitive types, object internal names, arrays up to the JVM limit of 255 dimensions, and void method returns. It rejects void fields/parameters, malformed object names, missing delimiters, and trailing data. Slot accounting follows JVM local-variable rules: `long` and `double` consume two slots, while arrays and references consume one. `validate_method_parameter_slots` enforces the 255-slot method parameter limit and can include the receiver slot for instance methods; the caller must supply the correct static/instance context.

## Next

- Resolve constant-pool references into typed symbols.
- Parse generic Signature attributes separately from JVM descriptors.
- Add typed stack/local data-flow analysis and bytecode verifier checks.


## Typed operand-stack verification

The current verifier tracks JVM operand-stack value categories for integer, float, long, double, reference/null values, checks typed arithmetic and return instructions, and requires compatible stack states at control-flow merges. Long and double values count as two JVM stack slots. This is a deliberately bounded verification subset, not the complete JVM type verifier: object initialization, full local-variable type frames, invocation descriptors, arrays, and StackMapTable semantics remain future work.
