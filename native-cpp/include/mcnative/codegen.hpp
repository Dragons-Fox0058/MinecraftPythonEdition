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

void verify_typed_stack(const std::vector<std::uint8_t>& bytecode);
void verify_int_local_dataflow(const std::vector<std::uint8_t>& bytecode,
                               std::uint16_t max_locals);
[[nodiscard]] std::string generate_int_method_cpp(
    const std::vector<std::uint8_t>& bytecode, std::uint16_t max_locals = 0);
[[nodiscard]] std::string generate_static_int_invocation_cpp(
    const ClassFile& class_file, const Instruction& instruction);
[[nodiscard]] std::string generate_static_int_method_cpp(
    const ClassFile& class_file, const MemberInfo& method);

// Emits a declaration-only C++ namespace for every method in one parsed JVM class.
// Instance methods receive an explicit JObject* receiver as their first ABI argument.
[[nodiscard]] std::string generate_class_declarations_cpp(const ClassFile& class_file);

} // namespace mcnative::jvm
