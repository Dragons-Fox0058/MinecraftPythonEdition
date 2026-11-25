#include "mcnative/codegen.hpp"
#include "mcnative/control_flow.hpp"
#include "mcnative/descriptor.hpp"
#include "mcnative/symbol_table.hpp"

#include <algorithm>
#include <cctype>
#include <bit>
#include <limits>
#include <cstdint>
#include <optional>
#include <sstream>

namespace mcnative::jvm {
namespace {

enum class ValueType { Int, Float, Long, Double, Reference, Null };

int slot_width(ValueType type) {
    return type == ValueType::Long || type == ValueType::Double ? 2 : 1;
}

std::string type_name(ValueType type) {
    switch (type) {
    case ValueType::Int: return "int";
    case ValueType::Float: return "float";
    case ValueType::Long: return "long";
    case ValueType::Double: return "double";
    case ValueType::Reference: return "reference";
    case ValueType::Null: return "null";
    }
    return "unknown";
}

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


std::string generate_static_int_invocation_cpp(const ClassFile& class_file,
                                               const Instruction& instruction) {
    if (instruction.opcode != 0xb8) {
        throw CodegenError("static invocation code generation requires invokestatic");
    }

    MethodInvocation invocation;
    try {
        invocation = resolve_method_invocation(class_file, instruction);
    } catch (const ClassFileError& error) {
        throw CodegenError(std::string("cannot resolve static invocation: ") + error.what());
    }
    if (invocation.target.name == "<init>" || invocation.target.name == "<clinit>") {
        throw CodegenError("constructor and class-initializer calls are not supported by this backend");
    }

    MethodDescriptor descriptor;
    try {
        descriptor = parse_method_descriptor(invocation.target.descriptor);
    } catch (const DescriptorError& error) {
        throw CodegenError(std::string("invalid static invocation descriptor: ") + error.what());
    }
    if (!descriptor.parameters.empty() ||
        descriptor.return_type.kind != TypeKind::int_type ||
        descriptor.return_type.array_dimensions != 0) {
        throw CodegenError("static invocation backend currently supports only ()I methods");
    }

    std::ostringstream output;
    output << "stack.push_back(static_cast<std::uint32_t>("
           << "mcnative_generated::" << cpp_class_namespace(invocation.target.owner)
           << "::" << cpp_method_symbol(invocation.target.name, invocation.target.descriptor)
           << "()));";
    return output.str();
}


std::string generate_static_int_method_cpp(const ClassFile& class_file,
                                            const MemberInfo& method) {
    if ((method.access_flags & 0x0008U) == 0) {
        throw CodegenError("static invocation caller must be a static JVM method");
    }

    std::string method_descriptor;
    try {
        method_descriptor = class_file.utf8(method.descriptor_index);
    } catch (const ClassFileError& error) {
        throw CodegenError(std::string("cannot read caller descriptor: ") + error.what());
    }
    if (method_descriptor != "()I") {
        throw CodegenError("static invocation caller compiler currently supports only ()I methods");
    }

    const CodeAttribute* code = nullptr;
    for (const auto& attribute : method.attributes) {
        if (attribute.code) {
            code = &*attribute.code;
            break;
        }
    }
    if (code == nullptr) {
        throw CodegenError("static invocation caller has no Code attribute");
    }

    const auto instructions = decode_bytecode(code->bytecode);
    if (instructions.size() != 2 || instructions[0].opcode != 0xb8 ||
        instructions[1].opcode != 0xac || instructions[0].next_offset != instructions[1].offset) {
        throw CodegenError("static invocation caller currently requires exactly invokestatic; ireturn");
    }

    const auto call = generate_static_int_invocation_cpp(class_file, instructions[0]);
    std::ostringstream output;
    output << "// Generated by Minecraft C++ Native: class-aware invokestatic caller.\n"
           << "#include <cstdint>\n#include <stdexcept>\n#include <vector>\n\n"
           << "std::int32_t translated_method() {\n"
           << "    std::vector<std::uint32_t> stack;\n"
           << "    " << call << "\n"
           << "    if (stack.empty()) throw std::runtime_error(\"JVM operand stack underflow\");\n"
           << "    const auto result = stack.back(); stack.pop_back();\n"
           << "    if (!stack.empty()) throw std::runtime_error(\"invalid JVM stack at ireturn\");\n"
           << "    return static_cast<std::int32_t>(result);\n"
           << "}\n";
    return output.str();
}

void verify_typed_stack(const std::vector<std::uint8_t>& bytecode) {
    const auto graph = build_control_flow_graph(bytecode);
    if (graph.blocks.empty()) throw CodegenError("method has no basic blocks");
    using Stack = std::vector<ValueType>;
    std::vector<std::optional<Stack>> incoming(graph.blocks.size());
    std::vector<std::size_t> worklist{0};
    incoming[0] = Stack{};

    auto block_index = [&](std::uint32_t offset) {
        const auto it = std::find_if(graph.blocks.begin(), graph.blocks.end(),
            [&](const BasicBlock& block) { return block.start_offset == offset; });
        if (it == graph.blocks.end()) throw CodegenError("control-flow edge targets a missing basic block");
        return static_cast<std::size_t>(it - graph.blocks.begin());
    };

    while (!worklist.empty()) {
        const auto index = worklist.back();
        worklist.pop_back();
        Stack stack = *incoming[index];
        const auto& block = graph.blocks[index];

        auto pop = [&](ValueType expected, const Instruction& ins) {
            if (stack.empty()) throw CodegenError("operand-stack underflow at bytecode offset " +
                                                  std::to_string(ins.offset));
            const auto actual = stack.back();
            stack.pop_back();
            if (actual != expected) {
                throw CodegenError("type mismatch at bytecode offset " + std::to_string(ins.offset) +
                    ": expected " + type_name(expected) + ", found " + type_name(actual));
            }
        };
        auto push = [&](ValueType type) {
            stack.push_back(type);
            std::size_t slots = 0;
            for (const auto value : stack) slots += static_cast<std::size_t>(slot_width(value));
            if (slots > 65535) throw CodegenError("operand stack exceeds JVM slot limit");
        };

        for (const auto& ins : block.instructions) {
            const auto op = ins.opcode;
            if (op == 0x00 || op == 0x84 || (op == 0xc4 && ins.operands.at(0) == 0x84)) {
                continue;
            } else if ((op >= 0x02 && op <= 0x08) || op == 0x10 || op == 0x11 || is_iload(ins)) {
                push(ValueType::Int);
            } else if (op == 0x09 || op == 0x0a) {
                push(ValueType::Long);
            } else if (op >= 0x0b && op <= 0x0d) {
                push(ValueType::Float);
            } else if (op == 0x0e || op == 0x0f) {
                push(ValueType::Double);
            } else if (op == 0x01) {
                push(ValueType::Null);
            } else if (is_istore(ins)) {
                pop(ValueType::Int, ins);
            } else if (op >= 0x60 && op <= 0x73) {
                const auto group = (op - 0x60) % 4;
                const auto type = group == 0 ? ValueType::Int : group == 1 ? ValueType::Long :
                                  group == 2 ? ValueType::Float : ValueType::Double;
                pop(type, ins); pop(type, ins); push(type);
            } else if (op == 0x74 || op == 0x75 || op == 0x76 || op == 0x77) {
                const auto type = op == 0x74 ? ValueType::Int : op == 0x75 ? ValueType::Long :
                                  op == 0x76 ? ValueType::Float : ValueType::Double;
                pop(type, ins); push(type);
            } else if (op == 0x78 || op == 0x7a || op == 0x7c) {
                pop(ValueType::Int, ins); pop(ValueType::Int, ins); push(ValueType::Int);
            } else if (op == 0x79 || op == 0x7b || op == 0x7d) {
                pop(ValueType::Int, ins); pop(ValueType::Long, ins); push(ValueType::Long);
            } else if (op == 0x7e || op == 0x80 || op == 0x82) {
                pop(ValueType::Int, ins); pop(ValueType::Int, ins); push(ValueType::Int);
            } else if (op == 0x7f || op == 0x81 || op == 0x83) {
                pop(ValueType::Long, ins); pop(ValueType::Long, ins); push(ValueType::Long);
            } else if (op >= 0x91 && op <= 0x93) {
                pop(ValueType::Int, ins); push(ValueType::Int);
            } else if (op >= 0x99 && op <= 0x9e) {
                pop(ValueType::Int, ins);
            } else if (op >= 0x9f && op <= 0xa4) {
                pop(ValueType::Int, ins); pop(ValueType::Int, ins);
            } else if (op == 0xac) {
                pop(ValueType::Int, ins);
                if (!stack.empty()) throw CodegenError("non-empty operand stack at ireturn");
            } else if (op == 0xad) {
                pop(ValueType::Long, ins);
                if (!stack.empty()) throw CodegenError("non-empty operand stack at lreturn");
            } else if (op == 0xae) {
                pop(ValueType::Float, ins);
                if (!stack.empty()) throw CodegenError("non-empty operand stack at freturn");
            } else if (op == 0xaf) {
                pop(ValueType::Double, ins);
                if (!stack.empty()) throw CodegenError("non-empty operand stack at dreturn");
            } else if (op == 0xb0) {
                if (stack.empty() || (stack.back() != ValueType::Reference && stack.back() != ValueType::Null))
                    throw CodegenError("areturn requires a reference value");
                stack.pop_back();
                if (!stack.empty()) throw CodegenError("non-empty operand stack at areturn");
            } else if (op == 0xb1) {
                if (!stack.empty()) throw CodegenError("non-empty operand stack at return");
            } else if (op == 0xa7 || op == 0xc8) {
                // Unconditional control transfer.
            } else {
                unsupported(ins);
            }
        }

        for (const auto successor : block.successors) {
            const auto target = block_index(successor);
            if (!incoming[target]) {
                incoming[target] = stack;
                worklist.push_back(target);
            } else if (*incoming[target] != stack) {
                throw CodegenError("incompatible operand-stack types at control-flow merge " +
                                    std::to_string(successor));
            }
        }
    }
}


void verify_int_local_dataflow(const std::vector<std::uint8_t>& bytecode,
                               std::uint16_t max_locals) {
    const auto graph = build_control_flow_graph(bytecode);
    if (graph.blocks.empty()) throw CodegenError("method has no basic blocks");

    using State = std::vector<bool>;
    std::vector<std::optional<State>> incoming(graph.blocks.size());
    std::vector<std::size_t> worklist{0};
    incoming[0] = State(max_locals, false);

    auto block_index = [&](std::uint32_t offset) {
        const auto it = std::find_if(graph.blocks.begin(), graph.blocks.end(),
            [&](const BasicBlock& block) { return block.start_offset == offset; });
        if (it == graph.blocks.end())
            throw CodegenError("control-flow edge targets a missing basic block");
        return static_cast<std::size_t>(it - graph.blocks.begin());
    };

    while (!worklist.empty()) {
        const auto index = worklist.back();
        worklist.pop_back();
        auto initialized = *incoming[index];

        for (const auto& ins : graph.blocks[index].instructions) {
            const auto op = ins.opcode;
            if (is_iload(ins) || is_istore(ins) ||
                op == 0x84 || (op == 0xc4 && ins.operands.at(0) == 0x84)) {
                const auto slot = local_index(ins);
                require_local(slot, max_locals, ins);
                if (is_iload(ins) && !initialized[slot]) {
                    throw CodegenError("read of local variable " + std::to_string(slot) +
                        " that is not initialized on every incoming path at bytecode offset " +
                        std::to_string(ins.offset));
                }
                if (op == 0x84 || (op == 0xc4 && ins.operands.at(0) == 0x84)) {
                    if (!initialized[slot]) {
                        throw CodegenError("iinc of local variable " + std::to_string(slot) +
                            " that is not initialized at bytecode offset " +
                            std::to_string(ins.offset));
                    }
                } else if (is_istore(ins)) {
                    initialized[slot] = true;
                }
            }
        }

        for (const auto successor : graph.blocks[index].successors) {
            const auto target = block_index(successor);
            if (!incoming[target]) {
                incoming[target] = initialized;
                worklist.push_back(target);
                continue;
            }

            State merged = *incoming[target];
            bool changed = false;
            for (std::size_t slot = 0; slot < merged.size(); ++slot) {
                const bool value = merged[slot] && initialized[slot];
                if (value != merged[slot]) {
                    merged[slot] = value;
                    changed = true;
                }
            }
            if (changed) {
                incoming[target] = std::move(merged);
                worklist.push_back(target);
            }
        }
    }
}

std::string generate_int_method_cpp(const std::vector<std::uint8_t>& bytecode,
                                   std::uint16_t max_locals) {
    const auto instructions = decode_bytecode(bytecode);
    if (instructions.empty()) {
        throw CodegenError("cannot generate a method from empty bytecode");
    }
    // Validate all branch destinations before emitting labels and gotos.
    verify_typed_stack(bytecode);
    verify_int_local_dataflow(bytecode, max_locals);

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
           << "#include <bit>\n#include <cstdint>\n#include <limits>\n#include <stdexcept>\n#include <vector>\n\n"
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

