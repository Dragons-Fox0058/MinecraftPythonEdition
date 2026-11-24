#include "mcnative/bytecode.hpp"

#include <array>
#include <sstream>

namespace mcnative::jvm {
namespace {

constexpr std::array<std::string_view, 202> names{
    "nop","aconst_null","iconst_m1","iconst_0","iconst_1","iconst_2","iconst_3","iconst_4","iconst_5",
    "lconst_0","lconst_1","fconst_0","fconst_1","fconst_2","dconst_0","dconst_1","bipush","sipush",
    "ldc","ldc_w","ldc2_w","iload","lload","fload","dload","aload","iload_0","iload_1","iload_2","iload_3",
    "lload_0","lload_1","lload_2","lload_3","fload_0","fload_1","fload_2","fload_3","dload_0","dload_1",
    "dload_2","dload_3","aload_0","aload_1","aload_2","aload_3","iaload","laload","faload","daload","aaload",
    "baload","caload","saload","istore","lstore","fstore","dstore","astore","istore_0","istore_1","istore_2",
    "istore_3","lstore_0","lstore_1","lstore_2","lstore_3","fstore_0","fstore_1","fstore_2","fstore_3",
    "dstore_0","dstore_1","dstore_2","dstore_3","astore_0","astore_1","astore_2","astore_3","iastore",
    "lastore","fastore","dastore","aastore","bastore","castore","sastore","pop","pop2","dup","dup_x1",
    "dup_x2","dup2","dup2_x1","dup2_x2","swap","iadd","ladd","fadd","dadd","isub","lsub","fsub","dsub",
    "imul","lmul","fmul","dmul","idiv","ldiv","fdiv","ddiv","irem","lrem","frem","drem","ineg","lneg",
    "fneg","dneg","ishl","lshl","ishr","lshr","iushr","lushr","iand","land","ior","lor","ixor","lxor",
    "iinc","i2l","i2f","i2d","l2i","l2f","l2d","f2i","f2l","f2d","d2i","d2l","d2f","i2b","i2c","i2s",
    "lcmp","fcmpl","fcmpg","dcmpl","dcmpg","ifeq","ifne","iflt","ifge","ifgt","ifle","if_icmpeq",
    "if_icmpne","if_icmplt","if_icmpge","if_icmpgt","if_icmple","if_acmpeq","if_acmpne","goto","jsr",
    "ret","tableswitch","lookupswitch","ireturn","lreturn","freturn","dreturn","areturn","return","getstatic",
    "putstatic","getfield","putfield","invokevirtual","invokespecial","invokestatic","invokeinterface",
    "invokedynamic","new","newarray","anewarray","arraylength","athrow","checkcast","instanceof","monitorenter",
    "monitorexit","wide","multianewarray","ifnull","ifnonnull","goto_w","jsr_w"
};

[[noreturn]] void fail(std::uint32_t offset, const std::string& reason) {
    std::ostringstream out;
    out << "invalid bytecode at offset " << offset << ": " << reason;
    throw BytecodeError(out.str());
}

std::uint32_t read_u4(const std::vector<std::uint8_t>& code, std::size_t pos,
                      std::uint32_t instruction_offset) {
    if (pos + 4 > code.size()) fail(instruction_offset, "truncated 32-bit operand");
    return (static_cast<std::uint32_t>(code[pos]) << 24U) |
           (static_cast<std::uint32_t>(code[pos + 1]) << 16U) |
           (static_cast<std::uint32_t>(code[pos + 2]) << 8U) |
           static_cast<std::uint32_t>(code[pos + 3]);
}

} // namespace

std::string_view opcode_name(std::uint8_t opcode) noexcept {
    if (opcode < names.size()) return names[opcode];
    return "<reserved>";
}

std::vector<Instruction> decode_bytecode(const std::vector<std::uint8_t>& code) {
    std::vector<Instruction> result;
    std::size_t pc = 0;
    while (pc < code.size()) {
        const auto start = pc;
        const auto opcode = code[pc++];
        if (opcode >= names.size()) fail(static_cast<std::uint32_t>(start), "reserved opcode");

        Instruction instruction;
        instruction.offset = static_cast<std::uint32_t>(start);
        instruction.opcode = opcode;

        auto fixed = [&](std::size_t count) {
            if (pc + count > code.size()) fail(instruction.offset, "truncated instruction operands");
            instruction.operands.insert(instruction.operands.end(),
                                        code.begin() + static_cast<std::ptrdiff_t>(pc),
                                        code.begin() + static_cast<std::ptrdiff_t>(pc + count));
            pc += count;
        };

        if (opcode == 0xaa || opcode == 0xab) {
            while ((pc & 3U) != 0U) {
                if (pc >= code.size()) fail(instruction.offset, "truncated switch padding");
                instruction.operands.push_back(code[pc++]);
            }
            fixed(4); // default
            if (opcode == 0xaa) {
                fixed(4); // low
                fixed(4); // high
                const auto low_pos = pc - 8;
                const auto low = static_cast<std::int32_t>(read_u4(code, low_pos, instruction.offset));
                const auto high = static_cast<std::int32_t>(read_u4(code, low_pos + 4, instruction.offset));
                if (high < low) fail(instruction.offset, "tableswitch high is below low");
                const auto count = static_cast<std::uint64_t>(static_cast<std::int64_t>(high) - low + 1);
                if (count > (code.size() - pc) / 4) fail(instruction.offset, "truncated tableswitch jump table");
                fixed(static_cast<std::size_t>(count * 4));
            } else {
                fixed(4); // npairs
                const auto pairs_pos = pc - 4;
                const auto pairs = static_cast<std::int32_t>(read_u4(code, pairs_pos, instruction.offset));
                if (pairs < 0) fail(instruction.offset, "negative lookupswitch npairs");
                if (static_cast<std::uint64_t>(pairs) > (code.size() - pc) / 8)
                    fail(instruction.offset, "truncated lookupswitch pair table");
                fixed(static_cast<std::size_t>(pairs) * 8);
            }
        } else if (opcode == 0xc4) {
            if (pc >= code.size()) fail(instruction.offset, "truncated wide opcode");
            const auto modified = code[pc++];
            instruction.operands.push_back(modified);
            if ((modified >= 0x15 && modified <= 0x19) ||
                (modified >= 0x36 && modified <= 0x3a) || modified == 0xa9) {
                fixed(2);
            } else if (modified == 0x84) {
                fixed(4);
            } else {
                fail(instruction.offset, "wide prefix applied to illegal opcode");
            }
        } else {
            std::size_t operand_count = 0;
            if (opcode == 0x10 || opcode == 0x12 ||
                (opcode >= 0x15 && opcode <= 0x19) ||
                (opcode >= 0x36 && opcode <= 0x3a) || opcode == 0xa9 || opcode == 0xbc) {
                operand_count = 1;
            } else if (opcode == 0x11 || opcode == 0x13 || opcode == 0x14 ||
                       opcode == 0x84 || (opcode >= 0x99 && opcode <= 0xa8) ||
                       (opcode >= 0xb2 && opcode <= 0xb8) || opcode == 0xbb ||
                       opcode == 0xbd || opcode == 0xc0 || opcode == 0xc1 ||
                       opcode == 0xc6 || opcode == 0xc7) {
                operand_count = 2;
            } else if (opcode == 0xb9 || opcode == 0xba || opcode == 0xc8 ||
                       opcode == 0xc9) {
                operand_count = 4;
            } else if (opcode == 0xc5) {
                operand_count = 3;
            }
            fixed(operand_count);
        }

        instruction.next_offset = static_cast<std::uint32_t>(pc);
        result.push_back(std::move(instruction));
    }
    return result;
}

} // namespace mcnative::jvm
