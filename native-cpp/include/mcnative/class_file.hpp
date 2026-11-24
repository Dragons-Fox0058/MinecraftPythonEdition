#pragma once

#include <cstdint>
#include <filesystem>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace mcnative::jvm {

class ClassFileError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

struct ConstantPoolEntry {
    std::uint8_t tag{};
    std::uint16_t first_index{};
    std::uint16_t second_index{};
    std::uint32_t bits{};
    std::uint64_t wide_bits{};
    std::string text;
};

struct ExceptionHandler {
    std::uint16_t start_pc{};
    std::uint16_t end_pc{};
    std::uint16_t handler_pc{};
    std::uint16_t catch_type{};
};

struct CodeAttribute {
    std::uint16_t max_stack{};
    std::uint16_t max_locals{};
    std::vector<std::uint8_t> bytecode;
    std::vector<ExceptionHandler> exception_table;
};

struct AttributeInfo {
    std::uint16_t name_index{};
    std::uint32_t length{};
    std::optional<CodeAttribute> code;
};

struct MemberInfo {
    std::uint16_t access_flags{};
    std::uint16_t name_index{};
    std::uint16_t descriptor_index{};
    std::vector<AttributeInfo> attributes;
};

struct ClassFile {
    std::uint16_t minor_version{};
    std::uint16_t major_version{};
    std::uint16_t access_flags{};
    std::uint16_t this_class{};
    std::uint16_t super_class{};
    std::vector<ConstantPoolEntry> constant_pool; // index zero is unused
    std::vector<std::uint16_t> interfaces;
    std::vector<MemberInfo> fields;
    std::vector<MemberInfo> methods;
    std::vector<AttributeInfo> attributes;

    [[nodiscard]] const ConstantPoolEntry& cp(std::uint16_t index) const;
    [[nodiscard]] std::string utf8(std::uint16_t index) const;
    [[nodiscard]] std::string class_name(std::uint16_t class_index) const;
    [[nodiscard]] std::string this_name() const;
    [[nodiscard]] std::string super_name() const;
};

class ClassFileParser {
public:
    [[nodiscard]] static ClassFile parse(const std::vector<std::uint8_t>& bytes);
    [[nodiscard]] static ClassFile parse_file(const std::filesystem::path& path);
};

} // namespace mcnative::jvm
