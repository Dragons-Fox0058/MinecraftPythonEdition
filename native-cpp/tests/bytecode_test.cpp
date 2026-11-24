#include "mcnative/bytecode.hpp"

#include <cassert>
#include <cstdint>
#include <vector>

using mcnative::jvm::BytecodeError;
using mcnative::jvm::decode_bytecode;

int main() {
    const auto simple = decode_bytecode({0x10, 0x2a, 0x84, 0x01, 0x02, 0xb1});
    assert(simple.size() == 3);
    assert(simple[0].offset == 0 && simple[0].next_offset == 2);
    assert(simple[1].opcode == 0x84 && simple[1].operands.size() == 2);
    assert(simple[2].opcode == 0xb1);

    const auto wide = decode_bytecode({0xc4, 0x84, 0x01, 0x00, 0x00, 0x05});
    assert(wide.size() == 1);
    assert(wide[0].operands.size() == 5);

    // tableswitch at offset zero: one padding byte, default, low=0, high=0, one jump.
    const auto table = decode_bytecode({
        0xaa, 0x00,
        0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00
    });
    assert(table.size() == 1);
    assert(table[0].next_offset == 18);

    bool rejected = false;
    try {
        (void)decode_bytecode({0x10});
    } catch (const BytecodeError&) {
        rejected = true;
    }
    assert(rejected);
    return 0;
}
