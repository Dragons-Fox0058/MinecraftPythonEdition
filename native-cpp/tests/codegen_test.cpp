#include "mcnative/codegen.hpp"

#include <cassert>
#include <string>

using namespace mcnative::jvm;

int main() {
    const auto generated = generate_int_method_cpp({0x05, 0x06, 0x60, 0xac}); // 2 + 3
    assert(generated.find("std::int32_t translated_method()") != std::string::npos);
    assert(generated.find("lhs + rhs") != std::string::npos);
    assert(generated.find("std::bit_cast<std::int32_t>") != std::string::npos);

    const auto negative = generate_int_method_cpp({0x10, 0xff, 0xac}); // bipush -1
    assert(negative.find("static_cast<std::uint32_t>(-1)") != std::string::npos);

    bool rejected = false;
    try {
        (void)generate_int_method_cpp({0x15, 0x00, 0xac}); // iload is not supported yet
    } catch (const CodegenError&) {
        rejected = true;
    }
    assert(rejected);

    rejected = false;
    try {
        (void)generate_int_method_cpp({0x60, 0xac}); // stack underflow
    } catch (const CodegenError&) {
        rejected = true;
    }
    assert(rejected);
    return 0;
}
