# Bytecode and Descriptor Analysis

## Bytecode decoder

The instruction decoder converts a Code attribute's byte array into offset-preserving instruction records. It handles fixed-width operands, branch operands, constant-pool operands, and the variable-length \`tableswitch\`, \`lookupswitch\`, and \`wide\` forms. Each record retains raw operand bytes and the next instruction offset.

The decoder rejects truncated instructions, invalid switch bounds, negative lookup pair counts, illegal \`wide\` sub-opcodes, and reserved opcodes. It does not yet resolve branch targets, constant-pool operands, stack effects, or verify control flow.

## Descriptor parser

Field and method descriptor parsing supports primitive types, object internal names, arrays up to the JVM limit of 255 dimensions, and void method returns. It rejects void fields/parameters, malformed object names, missing delimiters, and trailing data.

## Next

- Resolve constant-pool references into typed symbols.
- Parse generic Signature attributes separately from JVM descriptors.
- Decode branch targets and build basic blocks / a control-flow graph.
- Add stack/local data-flow analysis and bytecode verifier checks.
