#pragma once

#include "mcnative/bytecode.hpp"

#include <stdexcept>
#include <string>
#include <vector>

namespace mcnative::jvm {

class CodegenError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

// Emits a standalone C++20 function for the deliberately small, straight-line
// JVM int-bytecode subset documented in docs/CODE_GENERATION.md.
[[nodiscard]] std::string generate_int_method_cpp(const std::vector<std::uint8_t>& bytecode);

} // namespace mcnative::jvm
