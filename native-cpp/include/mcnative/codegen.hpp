#pragma once

#include "mcnative/bytecode.hpp"

#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace mcnative::jvm {

class CodegenError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

// Emits a standalone C++20 function for the supported straight-line JVM int subset.
// max_locals comes from the method's Code attribute; all locals start at JVM default zero.
[[nodiscard]] std::string generate_int_method_cpp(
    const std::vector<std::uint8_t>& bytecode, std::uint16_t max_locals = 0);

} // namespace mcnative::jvm
