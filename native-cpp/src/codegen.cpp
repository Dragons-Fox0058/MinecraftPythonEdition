#include "mcnative/codegen.hpp"
#include "mcnative/control_flow.hpp"

#include <bit>
#include <cstdint>
#include <limits>
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

std::int32_t signed_u32(std::uint32_t value) {
    return value < 0x80000000U ? static_cast<std::int32_t>(value)
        : static_cast<std::int32_t>(static_cast<std::int64_t>(value) - 0x100000000LL);
}

std::uint32_t operand_u4(const Instruction& instruction) {
    return (static_cast<std::uint32_t>(instruction.operands.at(0)) << 24U) |
           (static_cast<std::uint32_t>(instruction.operands.at(1)) << 16U) |
           (static_cast<std::uint32_t>(instruction.operands.at(2)) << 8U) |
           static_cast<std::uint32_t>(instruction.operands.at(3));
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
    return op == 0x15 || (op >= 0x1a && op <= 0x1d) ||
           (op == 0xc4 && instruction.operands.at(0) == 0x15);
}

bool is_istore(const Instruction& instruction) {
    const auto op = instruction.opcode;
    return op == 0x36 || (op >= 0x3b && op <= 0x3e) ||
           (op == 0xc4 && instruction.operands.at(0) == 0x36);
}

std::string label(std::uint32_t offset) {
    return "L" + std::to_string(offset);
}

[[noreturn]] void unsupported(const Instruction& instruction) {
    std::ostringstream out;
    out << "C++ code generation does not support opcode "
        << opcode_name(instruction.opcode) << " (0x" << std::hex
        << static_cast<unsigned>(instruction.opcode) << ") at bytecode offset "
        << std::dec << instruction.offset;
    throw CodegenError(out.str());
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
    // Validate all branch destinations before emitting labels and gotos.
    (void)build_control_flow_graph(bytecode);

    std::ostringstream body;
    bool has_return = false;

    for (const auto& instruction : instructions) {
        const auto op = instruction.opcode;
        body << label(instruction.offset) << ":\n";

        if (op >= 0x02 && op <= 0x08) {
            const auto value = static_cast<std::int32_t>(op) - 3;
            body << "    stack.push_back(static_cast<std::uint32_t>(" << value << "));\n";
        } else if (op == 0x10) {
            const auto value = signed_u8(instruction.operands.at(0));
            body << "    stack.push_back(static_cast<std::uint32_t>(" << value << "));\n";
        } else if (op == 0x11) {
            const auto value = signed_u16(operand_u2(instruction));
            body << "    stack.push_back(static_cast<std::uint32_t>(" << value << "));\n";
        } else if (is_iload(instruction)) {
            const auto index = local_index(instruction);
            require_local(index, max_locals, instruction);
            body << "    if (!locals_initialized[" << index << "]) throw std::runtime_error(\"read of uninitialized local\");\n"
                 << "    stack.push_back(locals[" << index << "]);\n";
        } else if (is_istore(instruction)) {
            const auto index = local_index(instruction);
            require_local(index, max_locals, instruction);
            body << "    locals[" << index << "] = pop_int();\n"
                 << "    locals_initialized[" << index << "] = true;\n";
        } else if (op == 0x84 || (op == 0xc4 && instruction.operands.at(0) == 0x84)) {
            const bool wide = op == 0xc4;
            const auto index = wide ? operand_u2(instruction, 1)
                                    : static_cast<std::uint16_t>(instruction.operands.at(0));
            const auto amount = wide ? signed_u16(operand_u2(instruction, 3))
                                     : signed_u8(instruction.operands.at(1));
            require_local(index, max_locals, instruction);
            body << "    if (!locals_initialized[" << index << "]) throw std::runtime_error(\"iinc on uninitialized local\");\n"
                 << "    locals[" << index << "] += static_cast<std::uint32_t>(" << amount << ");\n";
        } else if (op == 0x00) {
            body << "    // nop\n";
        } else if (op == 0x60 || op == 0x64 || op == 0x68 ||
                   op == 0x7e || op == 0x80 || op == 0x82 ||
                   op == 0x78 || op == 0x7a || op == 0x7c) {
            const char* operation = op == 0x60 ? "+" : op == 0x64 ? "-" :
                op == 0x68 ? "*" : op == 0x7e ? "&" : op == 0x80 ? "|" :
                op == 0x82 ? "^" : op == 0x78 ? "<<" : op == 0x7a ? ">>" : ">>>"; 
            body << "    { const auto rhs = pop_int(); const auto lhs = pop_int();\n";
            if (op == 0x7a) {
                body << "      stack.push_back(static_cast<std::uint32_t>(std::bit_cast<std::int32_t>(lhs) >> (rhs & 0x1FU))); }\n";
            } else if (op == 0x7c) {
                body << "      stack.push_back(lhs >> (rhs & 0x1FU)); }\n";
            } else if (op == 0x78) {
                body << "      stack.push_back(lhs << (rhs & 0x1FU)); }\n";
            } else if (op == 0x60 || op == 0x64 || op == 0x68 ||
                       op == 0x7e || op == 0x80 || op == 0x82) {
                body << "      stack.push_back(lhs " << operation << " rhs); }\n";
            }
        } else if (op == 0x6c || op == 0x70) {
            body << "    { const auto rhs = std::bit_cast<std::int32_t>(pop_int());\n"
                 << "      const auto lhs = std::bit_cast<std::int32_t>(pop_int());\n"
                 << "      if (rhs == 0) throw std::runtime_error(\"integer division by zero\");\n";
            if (op == 0x6c) {
                body << "      if (lhs == std::numeric_limits<std::int32_t>::min() && rhs == -1) stack.push_back(static_cast<std::uint32_t>(lhs));\n"
                     << "      else stack.push_back(static_cast<std::uint32_t>(lhs / rhs)); }\n";
            } else {
                body << "      if (lhs == std::numeric_limits<std::int32_t>::min() && rhs == -1) stack.push_back(0U);\n"
                     << "      else stack.push_back(static_cast<std::uint32_t>(lhs % rhs)); }\n";
            }
        } else if (op == 0x74) {
            body << "    stack.push_back(0U - pop_int());\n";
        } else if (op == 0x91 || op == 0x92 || op == 0x93) {
            body << "    { const auto value = pop_int();\n";
            if (op == 0x91) {
                body << "      const auto v = value & 0xFFU; stack.push_back((v & 0x80U) ? (v | 0xFFFFFF00U) : v);\n";
            } else if (op == 0x92) {
                body << "      stack.push_back(value & 0xFFFFU);\n";
            } else {
                body << "      const auto v = value & 0xFFFFU; stack.push_back((v & 0x8000U) ? (v | 0xFFFF0000U) : v);\n";
            }
            body << "    }\n";
        } else if (op >= 0x99 && op <= 0x9e) {
            const auto target = static_cast<std::int64_t>(instruction.offset) +
                                signed_u16(operand_u2(instruction));
            const char* condition = op == 0x99 ? " == 0" : op == 0x9a ? " != 0" :
                op == 0x9b ? " < 0" : op == 0x9c ? " >= 0" :
                op == 0x9d ? " > 0" : " <= 0";
            body << "    if (std::bit_cast<std::int32_t>(pop_int())" << condition
                 << ") goto " << label(static_cast<std::uint32_t>(target)) << ";\n";
        } else if (op >= 0x9f && op <= 0xa4) {
            const auto target = static_cast<std::int64_t>(instruction.offset) +
                                signed_u16(operand_u2(instruction));
            const char* condition = op == 0x9f ? " == " : op == 0xa0 ? " != " :
                op == 0xa1 ? " < " : op == 0xa2 ? " >= " :
                op == 0xa3 ? " > " : " <= ";
            body << "    { const auto rhs = std::bit_cast<std::int32_t>(pop_int());\n"
                 << "      const auto lhs = std::bit_cast<std::int32_t>(pop_int());\n"
                 << "      if (lhs" << condition << "rhs) goto "
                 << label(static_cast<std::uint32_t>(target)) << "; }\n";
        } else if (op == 0xa7) {
            const auto target = static_cast<std::int64_t>(instruction.offset) +
                                signed_u16(operand_u2(instruction));
            body << "    goto " << label(static_cast<std::uint32_t>(target)) << ";\n";
        } else if (op == 0xc8) {
            const auto target = static_cast<std::int64_t>(instruction.offset) +
                                signed_u32(operand_u4(instruction));
            body << "    goto " << label(static_cast<std::uint32_t>(target)) << ";\n";
        } else if (op == 0xac) {
            body << "    return std::bit_cast<std::int32_t>(pop_int());\n";
            has_return = true;
        } else {
            unsupported(instruction);
        }
    }

    if (!has_return) {
        throw CodegenError("integer method has no ireturn instruction");
    }

    std::ostringstream output;
    output << "// Generated by Minecraft C++ Native. JVM int subset with local and branch support.\n"
           << "#include <bit>\n#include <cstdint>\n#include <stdexcept>\n#include <vector>\n\n"
           << "std::int32_t translated_method() {\n"
           << "    std::vector<std::uint32_t> stack;\n"
           << "    std::vector<std::uint32_t> locals(" << max_locals << ", 0U);\n"
           << "    std::vector<bool> locals_initialized(" << max_locals << ", false);\n"
           << "    const auto pop_int = [&]() -> std::uint32_t {\n"
           << "        if (stack.empty()) throw std::runtime_error(\"JVM operand stack underflow\");\n"
           << "        const auto value = stack.back(); stack.pop_back(); return value;\n"
           << "    };\n"
           << body.str()
           << "    throw std::runtime_error(\"JVM method reached end without ireturn\");\n"
           << "}\n";
    return output.str();
}

} // namespace mcnative::jvm
