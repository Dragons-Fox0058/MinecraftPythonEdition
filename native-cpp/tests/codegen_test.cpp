#include "mcnative/codegen.hpp"

#include <cassert>
#include <cstdint>
#include <string>

using namespace mcnative::jvm;

int main() {
    // invokestatic #6 -> Test.call()I becomes a deterministic generated C++ symbol.
    ClassFile invocation_class;
    invocation_class.constant_pool.resize(7);
    invocation_class.constant_pool[1].tag = 1;
    invocation_class.constant_pool[1].text = "Test";
    invocation_class.constant_pool[2].tag = 7;
    invocation_class.constant_pool[2].first_index = 1;
    invocation_class.constant_pool[3].tag = 1;
    invocation_class.constant_pool[3].text = "call";
    invocation_class.constant_pool[4].tag = 1;
    invocation_class.constant_pool[4].text = "()I";
    invocation_class.constant_pool[5].tag = 12;
    invocation_class.constant_pool[5].first_index = 3;
    invocation_class.constant_pool[5].second_index = 4;
    invocation_class.constant_pool[6].tag = 10;
    invocation_class.constant_pool[6].first_index = 2;
    invocation_class.constant_pool[6].second_index = 5;

    const auto static_call = generate_static_int_invocation_cpp(
        invocation_class, Instruction{0, 0xb8, {0x00, 0x06}, 3});
    assert(static_call ==
        "stack.push_back(static_cast<std::uint32_t>(mcnative_generated::C_Test::call()));");

    bool invocation_rejected = false;
    try {
        (void)generate_static_int_invocation_cpp(
            invocation_class, Instruction{0, 0xb6, {0x00, 0x06}, 3});
    } catch (const CodegenError&) {
        invocation_rejected = true;
    }
    assert(invocation_rejected);

    MemberInfo caller;
    caller.access_flags = 0x0008; // ACC_STATIC
    caller.name_index = 3;
    caller.descriptor_index = 4;
    AttributeInfo caller_code;
    caller_code.code = CodeAttribute{1, 0, {0xb8, 0x00, 0x06, 0xac}, {}};
    caller.attributes.push_back(caller_code);
    const auto compiled_caller = generate_static_int_method_cpp(invocation_class, caller);
    assert(compiled_caller.find(
        "stack.push_back(static_cast<std::uint32_t>(mcnative_generated::C_Test::call()));")
        != std::string::npos);
    assert(compiled_caller.find("return static_cast<std::int32_t>(result);")
        != std::string::npos);

    bool caller_rejected = false;
    try {
        auto non_static = caller;
        non_static.access_flags = 0;
        (void)generate_static_int_method_cpp(invocation_class, non_static);
    } catch (const CodegenError&) {
        caller_rejected = true;
    }
    assert(caller_rejected);


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

    rejected = false;
    try {
        (void)generate_int_method_cpp({0x1a, 0xac}, 1);
    } catch (const CodegenError&) {
        rejected = true;
    }
    assert(rejected); // definite-initialization is now rejected statically

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


    // A local initialized on only one incoming branch must be rejected.
    rejected = false;
    try {
        verify_int_local_dataflow(
            {0x03, 0x99, 0x00, 0x08, 0x04, 0x3b, 0xa7, 0x00, 0x03, 0x1a, 0xac}, 1);
    } catch (const CodegenError&) {
        rejected = true;
    }
    assert(rejected);

    // Both incoming branches initialize local 0, so the merge is valid.
    verify_int_local_dataflow(
        {0x03, 0x99, 0x00, 0x08, 0x04, 0x3b, 0xa7, 0x00, 0x06,
         0x05, 0x3b, 0x00, 0x1a, 0xac}, 1);

    return 0;
}
