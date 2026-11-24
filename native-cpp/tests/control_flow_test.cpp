#include "mcnative/control_flow.hpp"

#include <cassert>

using namespace mcnative::jvm;

int main() {
    // iconst_0; ifeq +4; iconst_1; ireturn; iconst_2; ireturn
    const auto graph = build_control_flow_graph({0x03, 0x99, 0x00, 0x04, 0x04, 0xac, 0x05, 0xac});
    assert(graph.code_size == 8);
    assert(graph.blocks.size() == 3);
    assert(graph.blocks[0].start_offset == 0);
    assert(graph.blocks[0].successors.size() == 2);
    assert(graph.blocks[1].start_offset == 4);
    assert(graph.blocks[2].start_offset == 6);

    bool rejected = false;
    try {
        (void)build_control_flow_graph({0xa7, 0x7f, 0xff});
    } catch (const BytecodeError&) {
        rejected = true;
    }
    assert(rejected);
    return 0;
}
