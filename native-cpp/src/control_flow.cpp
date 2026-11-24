#include "mcnative/control_flow.hpp"

#include <algorithm>
#include <cstdint>
#include <map>
#include <set>
#include <sstream>
#include <unordered_map>

namespace mcnative::jvm {
namespace {

std::int32_t signed_u2(const std::vector<std::uint8_t>& bytes, std::size_t offset,
                       std::uint32_t instruction_offset) {
    if (offset + 2 > bytes.size()) {
        throw BytecodeError("truncated branch operand at bytecode offset " +
                            std::to_string(instruction_offset));
    }
    const auto value = static_cast<std::uint16_t>(
        (static_cast<std::uint16_t>(bytes[offset]) << 8U) | bytes[offset + 1]);
    return value < 0x8000U ? static_cast<std::int32_t>(value)
                           : static_cast<std::int32_t>(value) - 0x10000;
}

std::int32_t signed_u4(const std::vector<std::uint8_t>& bytes, std::size_t offset,
                       std::uint32_t instruction_offset) {
    if (offset + 4 > bytes.size()) {
        throw BytecodeError("truncated branch operand at bytecode offset " +
                            std::to_string(instruction_offset));
    }
    const auto value = (static_cast<std::uint32_t>(bytes[offset]) << 24U) |
                       (static_cast<std::uint32_t>(bytes[offset + 1]) << 16U) |
                       (static_cast<std::uint32_t>(bytes[offset + 2]) << 8U) |
                       static_cast<std::uint32_t>(bytes[offset + 3]);
    if (value < 0x80000000U) return static_cast<std::int32_t>(value);
    return static_cast<std::int32_t>(static_cast<std::int64_t>(value) - 0x100000000LL);
}

std::vector<std::int64_t> branch_targets(const Instruction& ins) {
    const auto op = ins.opcode;
    const auto& operands = ins.operands;
    if ((op >= 0x99 && op <= 0xa8) || op == 0xc6 || op == 0xc7) {
        const auto relative = signed_u2(operands, 0, ins.offset);
        return {static_cast<std::int64_t>(ins.offset) + relative};
    }
    if (op == 0xc8 || op == 0xc9) {
        const auto relative = signed_u4(operands, 0, ins.offset);
        return {static_cast<std::int64_t>(ins.offset) + relative};
    }
    if (op == 0xaa || op == 0xab) {
        const auto padding = (4U - ((ins.offset + 1U) & 3U)) & 3U;
        const auto default_offset = signed_u4(operands, padding, ins.offset);
        std::vector<std::int64_t> targets;
        targets.push_back(static_cast<std::int64_t>(ins.offset) + default_offset);
        if (op == 0xaa) {
            const auto low = signed_u4(operands, padding + 4, ins.offset);
            const auto high = signed_u4(operands, padding + 8, ins.offset);
            const auto count = static_cast<std::uint64_t>(static_cast<std::int64_t>(high) - low + 1);
            for (std::uint64_t i = 0; i < count; ++i) {
                const auto relative = signed_u4(operands, padding + 12 + static_cast<std::size_t>(i) * 4,
                                                ins.offset);
                targets.push_back(static_cast<std::int64_t>(ins.offset) + relative);
            }
        } else {
            const auto pairs = signed_u4(operands, padding + 4, ins.offset);
            for (std::int32_t i = 0; i < pairs; ++i) {
                const auto relative = signed_u4(operands, padding + 8 + static_cast<std::size_t>(i) * 8 + 4,
                                                ins.offset);
                targets.push_back(static_cast<std::int64_t>(ins.offset) + relative);
            }
        }
        return targets;
    }
    return {};
}

bool is_conditional(std::uint8_t op) {
    return (op >= 0x99 && op <= 0xa6) || op == 0xc6 || op == 0xc7;
}

bool is_unconditional_jump(std::uint8_t op) {
    return op == 0xa7 || op == 0xc8;
}

bool is_terminal(std::uint8_t op) {
    return (op >= 0xac && op <= 0xb1) || op == 0xbf || op == 0xa9;
}

} // namespace

ControlFlowGraph build_control_flow_graph(const std::vector<std::uint8_t>& bytecode) {
    ControlFlowGraph graph;
    graph.code_size = static_cast<std::uint32_t>(bytecode.size());
    if (bytecode.empty()) return graph;

    const auto instructions = decode_bytecode(bytecode);
    std::unordered_map<std::uint32_t, std::size_t> instruction_by_offset;
    instruction_by_offset.reserve(instructions.size());
    for (std::size_t i = 0; i < instructions.size(); ++i) {
        instruction_by_offset.emplace(instructions[i].offset, i);
    }

    std::set<std::uint32_t> leaders{0};
    std::map<std::uint32_t, std::vector<std::uint32_t>> successors_by_offset;

    for (const auto& ins : instructions) {
        const auto targets = branch_targets(ins);
        auto& successors = successors_by_offset[ins.offset];
        for (const auto target : targets) {
            if (target < 0 || target >= static_cast<std::int64_t>(bytecode.size())) {
                throw BytecodeError("branch target outside Code attribute at offset " +
                                    std::to_string(ins.offset));
            }
            const auto target_offset = static_cast<std::uint32_t>(target);
            if (!instruction_by_offset.contains(target_offset)) {
                throw BytecodeError("branch target is not an instruction boundary at offset " +
                                    std::to_string(ins.offset));
            }
            leaders.insert(target_offset);
            successors.push_back(target_offset);
        }

        const bool conditional = is_conditional(ins.opcode);
        const bool jsr = ins.opcode == 0xa8 || ins.opcode == 0xc9;
        const bool terminal = is_terminal(ins.opcode);
        const bool unconditional = is_unconditional_jump(ins.opcode) ||
                                   ins.opcode == 0xaa || ins.opcode == 0xab;
        if (!terminal && !unconditional && ins.next_offset < bytecode.size()) {
            if (conditional || jsr) {
                leaders.insert(ins.next_offset);
            }
            successors.push_back(ins.next_offset);
        }
        if ((conditional || jsr || unconditional || terminal) &&
            ins.next_offset < bytecode.size()) {
            leaders.insert(ins.next_offset);
        }
    }

    std::vector<std::uint32_t> starts(leaders.begin(), leaders.end());
    for (std::size_t i = 0; i < starts.size(); ++i) {
        const auto start = starts[i];
        const auto end = i + 1 < starts.size() ? starts[i + 1] : graph.code_size;
        BasicBlock block;
        block.start_offset = start;
        block.end_offset = end;

        auto it = instruction_by_offset.find(start);
        if (it == instruction_by_offset.end()) {
            throw BytecodeError("basic block leader is not an instruction boundary");
        }
        for (std::size_t index = it->second; index < instructions.size() &&
             instructions[index].offset < end; ++index) {
            block.instructions.push_back(instructions[index]);
        }
        if (block.instructions.empty()) {
            throw BytecodeError("empty basic block generated");
        }

        const auto& last = block.instructions.back();
        const auto found = successors_by_offset.find(last.offset);
        if (found != successors_by_offset.end()) {
            block.successors = found->second;
        }
        std::sort(block.successors.begin(), block.successors.end());
        block.successors.erase(std::unique(block.successors.begin(), block.successors.end()),
                               block.successors.end());
        graph.blocks.push_back(std::move(block));
    }

    return graph;
}

} // namespace mcnative::jvm
