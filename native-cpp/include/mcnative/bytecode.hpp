#pragma once

#include <cstdint>
#include <stdexcept>
#include <string_view>
#include <vector>

namespace mcnative::jvm {

class BytecodeError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

struct Instruction {
    std::uint32_t offset{};
    std::uint8_t opcode{};
    std::vector<std::uint8_t> operands;
    std::uint32_t next_offset{};
};

[[nodiscard]] std::string_view opcode_name(std::uint8_t opcode) noexcept;
[[nodiscard]] std::vector<Instruction> decode_bytecode(const std::vector<std::uint8_t>& code);

} // namespace mcnative::jvm
