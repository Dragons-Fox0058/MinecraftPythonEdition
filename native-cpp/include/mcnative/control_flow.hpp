#pragma once

#include "mcnative/bytecode.hpp"

#include <cstdint>
#include <vector>

namespace mcnative::jvm {

struct BasicBlock {
    std::uint32_t start_offset{};
    std::uint32_t end_offset{}; // exclusive
    std::vector<Instruction> instructions;
    std::vector<std::uint32_t> successors; // block start offsets
};

struct ControlFlowGraph {
    std::uint32_t code_size{};
    std::vector<BasicBlock> blocks;
};

[[nodiscard]] ControlFlowGraph build_control_flow_graph(const std::vector<std::uint8_t>& bytecode);

} // namespace mcnative::jvm
