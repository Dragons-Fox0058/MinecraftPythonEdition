#include "mcnative/class_file.hpp"
#include "mcnative/codegen.hpp"

#include <algorithm>
#include <cassert>
#include <cstdint>
#include <vector>

using mcnative::jvm::ClassFileError;
using mcnative::jvm::ClassFileParser;

int main() {
    // Minimal valid class:
    // public class Test extends java/lang/Object { }
    const std::vector<std::uint8_t> minimal{
        0xCA,0xFE,0xBA,0xBE, 0x00,0x00, 0x00,0x3E, // magic, minor 0, major 62
        0x00,0x05, // constant_pool_count
        0x01,0x00,0x04,'T','e','s','t', // #1 Utf8 Test
        0x07,0x00,0x01, // #2 Class #1
        0x01,0x00,0x10,'j','a','v','a','/','l','a','n','g','/','O','b','j','e','c','t', // #3 Utf8
        0x07,0x00,0x03, // #4 Class #3
        0x00,0x21, // access flags
        0x00,0x02, // this
        0x00,0x04, // super
        0x00,0x00, // interfaces
        0x00,0x00, // fields
        0x00,0x00, // methods
        0x00,0x00  // attributes
    };

    const auto parsed = ClassFileParser::parse(minimal);
    assert(parsed.major_version == 62);
    assert(parsed.this_name() == "Test");
    assert(parsed.super_name() == "java/lang/Object");
    assert(parsed.fields.empty());
    assert(parsed.methods.empty());

    bool rejected = false;
    try {
        (void)ClassFileParser::parse({0x00, 0x01, 0x02});
    } catch (const ClassFileError&) {
        rejected = true;
    }
    assert(rejected);

    // Class with one public static int answer() method whose bytecode computes 2 + 3.
    const std::vector<std::uint8_t> with_method{
        0xCA,0xFE,0xBA,0xBE, 0x00,0x00, 0x00,0x3E,
        0x00,0x08,
        0x01,0x00,0x04,'T','e','s','t',
        0x07,0x00,0x01,
        0x01,0x00,0x10,'j','a','v','a','/','l','a','n','g','/','O','b','j','e','c','t',
        0x07,0x00,0x03,
        0x01,0x00,0x06,'a','n','s','w','e','r',
        0x01,0x00,0x03,'(',')','I',
        0x01,0x00,0x04,'C','o','d','e',
        0x00,0x21, 0x00,0x02, 0x00,0x04,
        0x00,0x00, 0x00,0x00,
        0x00,0x01,
        0x00,0x09, 0x00,0x05, 0x00,0x06,
        0x00,0x01,
        0x00,0x07, 0x00,0x00,0x00,0x10,
        0x00,0x02, 0x00,0x00, 0x00,0x00,0x00,0x04,
        0x05,0x06,0x60,0xAC,
        0x00,0x00, 0x00,0x00,
        0x00,0x00
    };
    const auto method_class = ClassFileParser::parse(with_method);
    assert(method_class.methods.size() == 1);
    assert(method_class.utf8(method_class.methods[0].name_index) == "answer");
    assert(method_class.methods[0].attributes.size() == 1);
    assert(method_class.methods[0].attributes[0].code.has_value());
    const auto generated = mcnative::jvm::generate_int_method_cpp(
        method_class.methods[0].attributes[0].code->bytecode);
    assert(generated.find("lhs + rhs") != std::string::npos);

    // Resolve both class and interface method references through NameAndType.
    const std::vector<std::uint8_t> with_method_refs{
        0xCA,0xFE,0xBA,0xBE, 0x00,0x00, 0x00,0x3E,
        0x00,0x0A,
        0x01,0x00,0x04,'T','e','s','t',
        0x07,0x00,0x01,
        0x01,0x00,0x10,'j','a','v','a','/','l','a','n','g','/','O','b','j','e','c','t',
        0x07,0x00,0x03,
        0x01,0x00,0x04,'c','a','l','l',
        0x01,0x00,0x03,'(',')','I',
        0x0C,0x00,0x05,0x00,0x06, // #7 NameAndType
        0x0A,0x00,0x02,0x00,0x07, // #8 Methodref
        0x0B,0x00,0x02,0x00,0x07, // #9 InterfaceMethodref
        0x00,0x21, 0x00,0x02, 0x00,0x04,
        0x00,0x00, 0x00,0x00, 0x00,0x00, 0x00,0x00
    };
    const auto refs_class = ClassFileParser::parse(with_method_refs);
    const auto class_ref = refs_class.method_reference(8);
    assert(class_ref.owner == "Test");
    assert(class_ref.name == "call");
    assert(class_ref.descriptor == "()I");
    assert(!class_ref.is_interface);
    const auto interface_ref = refs_class.method_reference(9);
    assert(interface_ref.owner == "Test");
    assert(interface_ref.is_interface);

    rejected = false;
    try {
        (void)refs_class.method_reference(1); // UTF-8 is not a method reference.
    } catch (const ClassFileError&) {
        rejected = true;
    }
    assert(rejected);

    auto invalid_descriptor_class = with_method;
    const std::vector<std::uint8_t> valid_descriptor{'(', ')', 'I'};
    const auto descriptor_pos = std::search(invalid_descriptor_class.begin(),
                                            invalid_descriptor_class.end(),
                                            valid_descriptor.begin(), valid_descriptor.end());
    assert(descriptor_pos != invalid_descriptor_class.end());
    invalid_descriptor_class[static_cast<std::size_t>(descriptor_pos - invalid_descriptor_class.begin() + 1)] = 'V';
    rejected = false;
    try {
        (void)ClassFileParser::parse(invalid_descriptor_class);
    } catch (const ClassFileError&) {
        rejected = true;
    }
    assert(rejected);

    auto empty_code_attribute = with_method;
    const std::vector<std::uint8_t> code_length_four{0x00, 0x00, 0x00, 0x04};
    const auto code_length_pos = std::search(empty_code_attribute.begin(), empty_code_attribute.end(),
                                             code_length_four.begin(), code_length_four.end());
    assert(code_length_pos != empty_code_attribute.end());
    std::fill(code_length_pos, code_length_pos + 4, 0x00);
    rejected = false;
    try {
        (void)ClassFileParser::parse(empty_code_attribute);
    } catch (const ClassFileError&) {
        rejected = true;
    }
    assert(rejected);

    auto missing_receiver_local = with_method;
    const std::vector<std::uint8_t> static_method_flags{0x00, 0x09, 0x00, 0x05};
    const auto flags_pos = std::search(missing_receiver_local.begin(), missing_receiver_local.end(),
                                       static_method_flags.begin(), static_method_flags.end());
    assert(flags_pos != missing_receiver_local.end());
    *(flags_pos + 1) = 0x01; // Make answer() an instance method without allocating its this slot.
    rejected = false;
    try {
        (void)ClassFileParser::parse(missing_receiver_local);
    } catch (const ClassFileError&) {
        rejected = true;
    }
    assert(rejected);

    // Exception table addresses must point to decoded instruction boundaries.
    auto exception_mid_instruction = with_method;
    const std::vector<std::uint8_t> original_code{0x05, 0x06, 0x60, 0xAC};
    const auto code_pos = std::search(exception_mid_instruction.begin(), exception_mid_instruction.end(),
                                      original_code.begin(), original_code.end());
    assert(code_pos != exception_mid_instruction.end());
    const auto code_offset = static_cast<std::size_t>(code_pos - exception_mid_instruction.begin());
    // Replace iconst_2 with bipush, making bytecode offset 1 the middle of an instruction.
    exception_mid_instruction[code_offset] = 0x10;
    exception_mid_instruction[code_offset + 1] = 0x05;
    exception_mid_instruction[code_offset + 2] = 0xAC;
    exception_mid_instruction.erase(exception_mid_instruction.begin() + static_cast<std::ptrdiff_t>(code_offset + 3));
    const std::vector<std::uint8_t> old_code_length{0x00, 0x00, 0x00, 0x04};
    const auto code_length_it = std::search(exception_mid_instruction.begin(), exception_mid_instruction.end(),
                                            old_code_length.begin(), old_code_length.end());
    assert(code_length_it != exception_mid_instruction.end());
    *(code_length_it + 3) = 0x03;
    // Code attribute shrinks by one byte: 16 -> 15.
    const std::vector<std::uint8_t> old_attribute_length{0x00, 0x00, 0x00, 0x10};
    const auto attribute_length_it = std::search(exception_mid_instruction.begin(), exception_mid_instruction.end(),
                                                 old_attribute_length.begin(), old_attribute_length.end());
    assert(attribute_length_it != exception_mid_instruction.end());
    *(attribute_length_it + 3) = 0x0F;
    // Locate exception_table_length immediately after the three byte instructions.
    const auto exception_count_pos = code_offset + 3;
    assert(exception_count_pos + 4 <= exception_mid_instruction.size());
    exception_mid_instruction[exception_count_pos] = 0x00;
    exception_mid_instruction[exception_count_pos + 1] = 0x01;
    // Handler: [0, 2), handler_pc=1 (inside bipush), catch_type=0.
    const std::vector<std::uint8_t> invalid_handler{0x00,0x00, 0x00,0x02, 0x00,0x01, 0x00,0x00};
    exception_mid_instruction.insert(exception_mid_instruction.begin() +
                                     static_cast<std::ptrdiff_t>(exception_count_pos + 2),
                                     invalid_handler.begin(), invalid_handler.end());
    rejected = false;
    try {
        (void)ClassFileParser::parse(exception_mid_instruction);
    } catch (const ClassFileError&) {
        rejected = true;
    }
    assert(rejected);

    return 0;
}
