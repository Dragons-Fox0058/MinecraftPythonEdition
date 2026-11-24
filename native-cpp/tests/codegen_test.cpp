#include "mcnative/codegen.hpp"

#include <cassert>
#include <string>

using namespace mcnative::jvm;

int main() {
    const auto generated = generate_int_method_cpp({0x05, 0x06, 0x60, 0xac});
    assert(generated.find("std::int32_t translated_method()") != std::string::npos);
    assert(generated.find("lhs + rhs") != std::string::npos);
    assert(generated.find("std::bit_cast<std::int32_t>") != std::string::npos);

    const auto negative = generate_int_method_cpp({0x10, 0xff, 0xac});
    assert(negative.find("static_cast<std::uint32_t>(-1)") != std::string::npos);

    // istore_0; iinc 0, 5; iload_0; iconst_2; imul; ireturn => 10
    const auto locals = generate_int_method_cpp(
        {0x06, 0x3b, 0x84, 0x00, 0x05, 0x1a, 0x05, 0x68, 0xac}, 1);
    assert(locals.find("locals[0] = stack.back()") != std::string::npos);
    assert(locals.find("locals[0] += static_cast<std::uint32_t>(5)") != std::string::npos);
    assert(locals.find("stack.push_back(locals[0])") != std::string::npos);

    // wide iload 256; ireturn
    const auto wide_load = generate_int_method_cpp({0x04, 0xc4, 0x36, 0x01, 0x00, 0xc4, 0x15, 0x01, 0x00, 0xac}, 257);
    assert(wide_load.find("stack.push_back(locals[256])") != std::string::npos);

    bool rejected = false;
    try {
        (void)generate_int_method_cpp({0x15, 0x00, 0xac}, 0);
    } catch (const CodegenError&) {
        rejected = true;
    }
    assert(rejected);

    rejected = false;
    try {
        (void)generate_int_method_cpp({0x1a, 0xac}, 0);
    } catch (const CodegenError&) {
        rejected = true;
    }
    assert(rejected);

    rejected = false;
    try {
        (void)generate_int_method_cpp({0x1a, 0xac}, 1); // uninitialized local
    } catch (const CodegenError&) {
        rejected = true;
    }
    assert(rejected);

    rejected = false;
    try {
        (void)generate_int_method_cpp({0x60, 0xac});
    } catch (const CodegenError&) {
        rejected = true;
    }
    assert(rejected);
    return 0;
}
