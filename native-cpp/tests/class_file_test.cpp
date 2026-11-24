#include "mcnative/class_file.hpp"

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
    return 0;
}
