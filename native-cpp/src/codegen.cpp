#include "mcnative/codegen.hpp"

#include <bit>
#include <cstdint>
#include <sstream>

namespace mcnative::jvm {
namespace {

std::uint16_t operand_u2(const Instruction& instruction, std::size_t offset = 0) {
    return static_cast<std::uint16_t>(
        (static_cast<std::uint16_t>(instruction.operands.at(offset)) << 8U) |
        instruction.operands.at(offset + 1));
}

std::int32_t signed_u8(std::uint8_t value) {
    return value < 0x80U ? static_cast<std::int32_t>(value)
                         : static_cast<std::int32_t>(value) - 0x100;
}

std::int32_t signed_u16(std::uint16_t value) {
    return value < 0x8000U ? static_cast<std::int32_t>(value)
                           : static_cast<std::int32_t>(value) - 0x10000;
}

std::uint16_t local_index(const Instruction& instruction) {
    const auto op = instruction.opcode;
    if (op == 0xc4) return operand_u2(instruction, 1);
    if ((op >= 0x1a && op <= 0x1d) || (op >= 0x3b && op <= 0x3e)) {
        return static_cast<std::uint16_t>(op <= 0x1d ? op - 0x1a : op - 0x3b);
    }
    return instruction.operands.at(0);
}

bool is_iload(const Instruction& instruction) {
    const auto op = instruction.opcode;
    return (op >= 0x15 && op <= 0x15) || (op >= 0x1a && op <= 0x1d) ||
           (op == 0xc4 && instruction.operands.at(0) == 0x15);
}

bool is_istore(const Instruction& instruction) {
    const auto op = instruction.opcode;
    return (op == 0x36) || (op >= 0x3b && op <= 0x3e) ||
           (op == 0xc4 && instruction.operands.at(0) == 0x36);
}

[[noreturn]] void unsupported(const Instruction& instruction) {
    std::ostringstream out;
    out << "C++ code generation does not support opcode "
        << opcode_name(instruction.opcode) << " (0x" << std::hex
        << static_cast<unsigned>(instruction.opcode) << ") at bytecode offset "
        << std::dec << instruction.offset;
    throw CodegenError(out.str());
}

void require_stack(std::size_t depth, std::size_t needed, const Instruction& instruction) {
    if (depth < needed) {
        throw CodegenError("integer stack underflow at bytecode offset " +
                           std::to_string(instruction.offset));
    }
}

void require_local(std::uint16_t index, std::uint16_t max_locals,
                   const Instruction& instruction) {
    if (index >= max_locals) {
        throw CodegenError("local-variable index " + std::to_string(index) +
                           " exceeds max_locals at bytecode offset " +
                           std::to_string(instruction.offset));
    }
}

} // namespace

std::string generate_int_method_cpp(const std::vector<std::uint8_t>& bytecode,
                                   std::uint16_t max_locals) {
    const auto instructions = decode_bytecode(bytecode);
    if (instructions.empty()) {
        throw CodegenError("cannot generate a method from empty bytecode");
    }

    std::ostringstream body;
    std::size_t stack_depth = 0;
    std::vector<bool> initialized_locals(max_locals, false);
    bool returned = false;

    for (const auto& instruction : instructions) {
        const auto op = instruction.opcode;
        if (returned) {
            throw CodegenError("instructions found after a terminal ireturn");
        }

        if (op >= 0x02 && op <= 0x08) {
            const auto value = static_cast<std::int32_t>(op) - 3;
            body << "    stack.push_back(static_cast<std::uint32_t>(" << value << "));\n";
            ++stack_depth;
        } else if (op == 0x10) {
            const auto value = signed_u8(instruction.operands.at(0));
            body << "    stack.push_back(static_cast<std::uint32_t>(" << value << "));\n";
            ++stack_depth;
        } else if (op == 0x11) {
            const auto value = signed_u16(operand_u2(instruction));
            body << "    stack.push_back(static_cast<std::uint32_t>(" << value << "));\n";
            ++stack_depth;
        } else if (is_iload(instruction)) {
            const auto index = local_index(instruction);
            require_local(index, max_locals, instruction);
            if (!initialized_locals[index]) {
                throw CodegenError("read of uninitialized local-variable slot " +
                                   std::to_string(index) + " at bytecode offset " +
                                   std::to_string(instruction.offset));
            }
            body << "    stack.push_back(locals[" << index << "]);\n";
            ++stack_depth;
        } else if (is_istore(instruction)) {
            const auto index = local_index(instruction);
            require_local(index, max_locals, instruction);
            require_stack(stack_depth, 1, instruction);
            body << "    locals[" << index << "] = stack.back(); stack.pop_back();\n";
            initialized_locals[index] = true;
            --stack_depth;
        } else if (op == 0x84 || (op == 0xc4 && instruction.operands.at(0) == 0x84)) {
            const bool wide = op == 0xc4;
            const auto index = wide ? operand_u2(instruction, 1)
                                    : static_cast<std::uint16_t>(instruction.operands.at(0));
            const auto amount = wide ? signed_u16(operand_u2(instruction, 3))
                                     : signed_u8(instruction.operands.at(1));
            require_local(index, max_locals, instruction);
            if (!initialized_locals[index]) {
                throw CodegenError("iinc on uninitialized local-variable slot " +
                                   std::to_string(index) + " at bytecode offset " +
                                   std::to_string(instruction.offset));
            }
            body << "    locals[" << index << "] += static_cast<std::uint32_t>("
                 << amount << ");\n";
        } else if (op == 0x00) {
            body << "    // nop\n";
        } else if (op == 0x60 || op == 0x64 || op == 0x68) {
            require_stack(stack_depth, 2, instruction);
            const char* operation = op == 0x60 ? "+" : (op == 0x64 ? "-" : "*");
            body << "    { const auto rhs = stack.back(); stack.pop_back();\n"
                 << "      const auto lhs = stack.back(); stack.pop_back();\n"
                 << "      stack.push_back(lhs " << operation << " rhs); }\n";
            --stack_depth;
        } else if (op == 0x74) {
            require_stack(stack_depth, 1, instruction);
            body << "    stack.back() = 0U - stack.back();\n";
        } else if (op == 0x91 || op == 0x92 || op == 0x93) {
            require_stack(stack_depth, 1, instruction);
            if (op == 0x91) {
                body << "    { const auto v = stack.back() & 0xFFU; stack.back() = (v & 0x80U) ? (v | 0xFFFFFF00U) : v; }\n";
            } else if (op == 0x92) {
                body << "    stack.back() &= 0xFFFFU;\n";
            } else {
                body << "    { const auto v = stack.back() & 0xFFFFU; stack.back() = (v & 0x8000U) ? (v | 0xFFFF0000U) : v; }\n";
            }
        } else if (op == 0xac) {
            require_stack(stack_depth, 1, instruction);
            body << "    return std::bit_cast<std::int32_t>(stack.back());\n";
            returned = true;
        } else {
            unsupported(instruction);
        }
    }

    if (!returned) {
        throw CodegenError("integer method has no ireturn instruction");
    }

    std::ostringstream output;
    output << "// Generated by Minecraft C++ Native. Straight-line JVM int subset.\n"
           << "#include <bit>\n#include <cstdint>\n#include <vector>\n\n"
           << "std::int32_t translated_method() {\n"
           << "    std::vector<std::uint32_t> stack;\n"
           << "    std::vector<std::uint32_t> locals(" << max_locals << ", 0U);\n"
           << body.str()
           << "}\n";
    return output.str();
}

} // namespace mcnative::jvm
