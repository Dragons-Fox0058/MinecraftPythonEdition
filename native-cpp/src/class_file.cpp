#include "mcnative/class_file.hpp"

#include <fstream>
#include <limits>
#include <sstream>

namespace mcnative::jvm {
namespace {

class Reader {
public:
    explicit Reader(const std::vector<std::uint8_t>& data) : data_(data) {}

    std::uint8_t u1() {
        require(1);
        return data_[position_++];
    }

    std::uint16_t u2() {
        const auto a = u1();
        const auto b = u1();
        return static_cast<std::uint16_t>((static_cast<std::uint16_t>(a) << 8U) | b);
    }

    std::uint32_t u4() {
        const auto a = u2();
        const auto b = u2();
        return (static_cast<std::uint32_t>(a) << 16U) | b;
    }

    std::uint64_t u8() {
        const auto a = u4();
        const auto b = u4();
        return (static_cast<std::uint64_t>(a) << 32U) | b;
    }

    std::vector<std::uint8_t> bytes(std::size_t count) {
        require(count);
        const auto begin = data_.begin() + static_cast<std::ptrdiff_t>(position_);
        std::vector<std::uint8_t> result(begin, begin + static_cast<std::ptrdiff_t>(count));
        position_ += count;
        return result;
    }

    void skip(std::size_t count) {
        require(count);
        position_ += count;
    }

    [[nodiscard]] std::size_t remaining() const noexcept {
        return data_.size() - position_;
    }

private:
    void require(std::size_t count) const {
        if (count > data_.size() - position_) {
            std::ostringstream message;
            message << "truncated class file at byte " << position_
                    << " (needed " << count << ", remaining " << (data_.size() - position_) << ')';
            throw ClassFileError(message.str());
        }
    }

    const std::vector<std::uint8_t>& data_;
    std::size_t position_{};
};

std::vector<AttributeInfo> read_attributes(Reader& reader,
                                           const std::vector<ConstantPoolEntry>& cp,
                                           bool parse_code) {
    const auto count = reader.u2();
    std::vector<AttributeInfo> attributes;
    attributes.reserve(count);

    for (std::uint16_t i = 0; i < count; ++i) {
        AttributeInfo attribute;
        attribute.name_index = reader.u2();
        attribute.length = reader.u4();
        if (attribute.name_index == 0 || attribute.name_index >= cp.size() ||
            cp[attribute.name_index].tag != 1) {
            throw ClassFileError("attribute name_index does not reference CONSTANT_Utf8");
        }

        const auto name = cp[attribute.name_index].text;
        if (parse_code && name == "Code") {
            Reader code_reader(reader.bytes(attribute.length));
            CodeAttribute code;
            code.max_stack = code_reader.u2();
            code.max_locals = code_reader.u2();
            const auto code_length = code_reader.u4();
            code.bytecode = code_reader.bytes(code_length);
            const auto exception_count = code_reader.u2();
            code.exception_table.reserve(exception_count);
            for (std::uint16_t j = 0; j < exception_count; ++j) {
                code.exception_table.push_back(
                    {code_reader.u2(), code_reader.u2(), code_reader.u2(), code_reader.u2()});
            }
            // Nested Code attributes (LineNumberTable, StackMapTable, LocalVariableTable, etc.)
            // are structurally skipped for now; their enclosing attribute boundary is validated.
            const auto nested_count = code_reader.u2();
            for (std::uint16_t j = 0; j < nested_count; ++j) {
                (void)code_reader.u2();
                const auto nested_length = code_reader.u4();
                code_reader.skip(nested_length);
            }
            if (code_reader.remaining() != 0) {
                throw ClassFileError("Code attribute length does not match its contents");
            }
            attribute.code = std::move(code);
        } else {
            reader.skip(attribute.length);
        }
        attributes.push_back(std::move(attribute));
    }
    return attributes;
}

std::vector<MemberInfo> read_members(Reader& reader,
                                     const std::vector<ConstantPoolEntry>& cp,
                                     bool methods) {
    const auto count = reader.u2();
    std::vector<MemberInfo> members;
    members.reserve(count);
    for (std::uint16_t i = 0; i < count; ++i) {
        MemberInfo member;
        member.access_flags = reader.u2();
        member.name_index = reader.u2();
        member.descriptor_index = reader.u2();
        if (member.name_index == 0 || member.name_index >= cp.size() || cp[member.name_index].tag != 1 ||
            member.descriptor_index == 0 || member.descriptor_index >= cp.size() ||
            cp[member.descriptor_index].tag != 1) {
            throw ClassFileError("member name or descriptor does not reference CONSTANT_Utf8");
        }
        member.attributes = read_attributes(reader, cp, methods);
        members.push_back(std::move(member));
    }
    return members;
}

} // namespace

const ConstantPoolEntry& ClassFile::cp(std::uint16_t index) const {
    if (index == 0 || index >= constant_pool.size()) {
        throw ClassFileError("constant-pool index out of range");
    }
    return constant_pool[index];
}

std::string ClassFile::utf8(std::uint16_t index) const {
    const auto& entry = cp(index);
    if (entry.tag != 1) {
        throw ClassFileError("constant-pool entry is not CONSTANT_Utf8");
    }
    return entry.text;
}

std::string ClassFile::class_name(std::uint16_t class_index) const {
    const auto& entry = cp(class_index);
    if (entry.tag != 7) {
        throw ClassFileError("class index does not reference CONSTANT_Class");
    }
    return utf8(entry.first_index);
}

std::string ClassFile::this_name() const {
    return class_name(this_class);
}

std::string ClassFile::super_name() const {
    return super_class == 0 ? std::string{} : class_name(super_class);
}

ClassFile ClassFileParser::parse(const std::vector<std::uint8_t>& bytes) {
    Reader reader(bytes);
    if (reader.u4() != 0xCAFEBABEU) {
        throw ClassFileError("invalid class-file magic (expected CAFEBABE)");
    }

    ClassFile result;
    result.minor_version = reader.u2();
    result.major_version = reader.u2();

    const auto cp_count = reader.u2();
    if (cp_count == 0) {
        throw ClassFileError("constant_pool_count must be greater than zero");
    }
    result.constant_pool.resize(cp_count);

    for (std::uint16_t i = 1; i < cp_count; ++i) {
        auto& entry = result.constant_pool[i];
        entry.tag = reader.u1();
        switch (entry.tag) {
        case 1: {
            const auto length = reader.u2();
            const auto data = reader.bytes(length);
            entry.text.assign(data.begin(), data.end()); // JVM modified UTF-8 bytes, preserved losslessly.
            break;
        }
        case 3:
        case 4:
            entry.bits = reader.u4();
            break;
        case 5:
        case 6:
            entry.wide_bits = reader.u8();
            if (++i < cp_count) {
                result.constant_pool[i].tag = 0; // reserved second slot per JVMS
            } else {
                throw ClassFileError("long/double constant has no reserved constant-pool slot");
            }
            break;
        case 7:
        case 8:
        case 16:
        case 19:
        case 20:
            entry.first_index = reader.u2();
            break;
        case 9:
        case 10:
        case 11:
        case 12:
        case 17:
        case 18:
            entry.first_index = reader.u2();
            entry.second_index = reader.u2();
            break;
        case 15:
            entry.first_index = reader.u1();
            entry.second_index = reader.u2();
            break;
        default:
            throw ClassFileError("unsupported/unknown constant-pool tag " + std::to_string(entry.tag));
        }
    }

    result.access_flags = reader.u2();
    result.this_class = reader.u2();
    result.super_class = reader.u2();

    // Validate class references immediately, including the special zero super_class for java/lang/Object.
    if (result.this_class == 0 || result.this_class >= result.constant_pool.size() ||
        result.constant_pool[result.this_class].tag != 7) {
        throw ClassFileError("this_class does not reference CONSTANT_Class");
    }
    if (result.super_class != 0 &&
        (result.super_class >= result.constant_pool.size() ||
         result.constant_pool[result.super_class].tag != 7)) {
        throw ClassFileError("super_class does not reference CONSTANT_Class");
    }

    const auto interface_count = reader.u2();
    result.interfaces.reserve(interface_count);
    for (std::uint16_t i = 0; i < interface_count; ++i) {
        const auto index = reader.u2();
        if (index == 0 || index >= result.constant_pool.size() ||
            result.constant_pool[index].tag != 7) {
            throw ClassFileError("interface index does not reference CONSTANT_Class");
        }
        result.interfaces.push_back(index);
    }

    result.fields = read_members(reader, result.constant_pool, false);
    result.methods = read_members(reader, result.constant_pool, true);
    result.attributes = read_attributes(reader, result.constant_pool, false);

    if (reader.remaining() != 0) {
        throw ClassFileError("unexpected trailing bytes after class-file structure");
    }
    return result;
}

ClassFile ClassFileParser::parse_file(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw ClassFileError("cannot open class file: " + path.string());
    }
    input.seekg(0, std::ios::end);
    const auto end = input.tellg();
    if (end < 0) {
        throw ClassFileError("cannot determine class-file size: " + path.string());
    }
    constexpr auto max_size = static_cast<std::streamoff>(256) * 1024 * 1024;
    if (end > max_size) {
        throw ClassFileError("class file exceeds 256 MiB safety limit");
    }
    input.seekg(0, std::ios::beg);
    std::vector<std::uint8_t> bytes(static_cast<std::size_t>(end));
    if (!bytes.empty()) {
        input.read(reinterpret_cast<char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
        if (!input) {
            throw ClassFileError("failed while reading class file: " + path.string());
        }
    }
    return parse(bytes);
}

} // namespace mcnative::jvm
