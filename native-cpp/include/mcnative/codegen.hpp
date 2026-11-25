#pragma once

#include "mcnative/bytecode.hpp"
#include "mcnative/class_file.hpp"

#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace mcnative::jvm {

class CodegenError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

// Verifies operand-stack value categories for the supported JVM verification subset.
// Category-2 values (long/double) occupy two JVM stack slots.
void verify_typed_stack(const std::vector<std::uint8_t>& bytecode);

// Verifies definite initialization of int locals across all reachable CFG paths.
void verify_int_local_dataflow(const std::vector<std::uint8_t>& bytecode,
                               std::uint16_t max_locals);

// Emits a standalone C++20 function for the supported straight-line JVM int subset.
// max_locals comes from the method's Code attribute; all locals start at JVM default zero.
[[nodiscard]] std::string generate_int_method_cpp(
    const std::vector<std::uint8_t>& bytecode, std::uint16_t max_locals = 0);

// Emits a stack-push statement for a parameterless static JVM method returning int.
// Generated class symbols use the stable C_<sanitized-internal-name> namespace convention.
[[nodiscard]] std::string generate_static_int_invocation_cpp(
    const ClassFile& class_file, const Instruction& instruction);

} // namespace mcnative::jvm
