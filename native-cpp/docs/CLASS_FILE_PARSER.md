# JVM Class-File Parser

The first analyzer component reads JVM class files from a user-selected local installation.

## Implemented

- Validates the \`CAFEBABE\` magic and reads minor/major versions.
- Parses constant-pool tags 1, 3–12, 15–20, including two-slot long/double entries.
- Retains modified UTF-8 payload bytes without lossy conversion.
- Reads class flags, this/super class, interfaces, fields, methods, and class attributes.
- Parses method \`Code\` attributes, including max stack/locals, raw bytecode, and exception table.
- Bounds-checks every read, skips unknown attributes by declared length, and rejects malformed/truncated files.
- CLI command: \`mc-native-tool inspect-class path/to/SomeClass.class\`.

## Deliberate limits

This is a structural parser, not yet a verifier, decompiler, or Java-to-C++ compiler. Nested Code attributes are length-checked and skipped. Constant-pool references beyond the class-name accessors are retained as indices for later semantic resolution. Modified UTF-8 is preserved as bytes; a dedicated decoder is still required before presenting arbitrary strings as Unicode.

The parser accepts class-file versions structurally and reports the actual version. It does not claim that all features of a particular future JVM version are semantically supported.
