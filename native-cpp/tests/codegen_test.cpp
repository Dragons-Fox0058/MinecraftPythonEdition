#include "mcnative/codegen.hpp"

#include <cassert>
#include <string>

using namespace mcnative::jvm;

int main() {
    verify_typed_stack({0x0a, 0xad}); // lconst_1; lreturn
    verify_typed_stack({0x0b, 0xae}); // fconst_0; freturn
    verify_typed_stack({0x0e, 0xaf}); // dconst_0; dreturn

    bool type_rejected = false;
    try {
        verify_typed_stack({0x0b, 0xac}); // float value cannot be returned as int
    } catch (const CodegenError&) {
        type_rejected = true;
    }
    assert(type_rejected);

    type_rejected = false;
    try {
        verify_typed_stack({0x05, 0x0b, 0x60, 0xac}); // iadd cannot consume float
    } catch (const CodegenError&) {
        type_rejected = true;
    }
    assert(type_rejected);

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

    // ifeq jumps over the first constant; the two paths merge at ireturn.
    const auto branched = generate_int_method_cpp(
        {0x03, 0x99, 0x00, 0x07, 0x04, 0xa7, 0x00, 0x04, 0x05, 0xac});
    assert(branched.find("if (std::bit_cast<std::int32_t>(pop_int()) == 0) goto L8;") != std::string::npos);
    assert(branched.find("goto L9;") != std::string::npos);
    assert(branched.find("L8:") != std::string::npos);
    assert(branched.find("L9:") != std::string::npos);

    const auto arithmetic = generate_int_method_cpp({0x10, 0x0c, 0x10, 0x03, 0x6c, 0xac});
    assert(arithmetic.find("lhs / rhs") != std::string::npos);
    assert(arithmetic.find("integer division by zero") != std::string::npos);

    const auto bitwise = generate_int_method_cpp({0x05, 0x06, 0x7e, 0xac});
    assert(bitwise.find("lhs & rhs") != std::string::npos);

    const auto unsigned_shift = generate_int_method_cpp({0x10, 0xff, 0x05, 0x7c, 0xac});
    assert(unsigned_shift.find("lhs >> (rhs & 0x1FU)") != std::string::npos);

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

    const auto guarded_uninitialized = generate_int_method_cpp({0x1a, 0xac}, 1);
    assert(guarded_uninitialized.find("read of uninitialized local") != std::string::npos);

    rejected = false;
    try {
        (void)generate_int_method_cpp({0x60, 0xac});
    } catch (const CodegenError&) {
        rejected = true;
    }
    assert(rejected);

    // A branch merge with stack depths 0 and 2 must be rejected statically.
    rejected = false;
    try {
        (void)generate_int_method_cpp(
            {0x03, 0x99, 0x00, 0x08, 0x04, 0x05, 0xa7, 0x00, 0x03, 0xac});
    } catch (const CodegenError&) {
        rejected = true;
    }
    assert(rejected);

    // Stack underflow is rejected before C++ is emitted.
    rejected = false;
    try {
        (void)generate_int_method_cpp({0x60, 0xac});
    } catch (const CodegenError&) {
        rejected = true;
    }
    assert(rejected);

    return 0;
}
