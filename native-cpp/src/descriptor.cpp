#include "mcnative/descriptor.hpp"

#include <cstddef>
#include <cctype>
#include <sstream>

namespace mcnative::jvm {
namespace {

class Parser {
public:
    explicit Parser(std::string_view input) : input_(input) {}

    JvmType type(bool allow_void) {
        unsigned dimensions = 0;
        while (peek() == '[') {
            ++position_;
            ++dimensions;
            if (dimensions > 255) fail("array dimensions exceed JVM limit of 255");
        }

        const char code = take();
        JvmType result;
        switch (code) {
        case 'B': result.kind = TypeKind::byte_type; break;
        case 'C': result.kind = TypeKind::char_type; break;
        case 'D': result.kind = TypeKind::double_type; break;
        case 'F': result.kind = TypeKind::float_type; break;
        case 'I': result.kind = TypeKind::int_type; break;
        case 'J': result.kind = TypeKind::long_type; break;
        case 'S': result.kind = TypeKind::short_type; break;
        case 'Z': result.kind = TypeKind::boolean_type; break;
        case 'V':
            if (!allow_void || dimensions != 0) fail("void is not valid in this position");
            result.kind = TypeKind::void_type;
            break;
        case 'L': {
            result.kind = TypeKind::object_type;
            const auto begin = position_;
            while (peek() != ';' && position_ < input_.size()) {
                const char c = take();
                if (c == '.' || c == '[' || c == '(' || c == ')') {
                    fail("invalid character in object internal name");
                }
            }
            if (position_ == begin) fail("empty object internal name");
            result.class_name = std::string(input_.substr(begin, position_ - begin));
            expect(';');
            break;
        }
        default:
            fail("unknown descriptor type code");
        }
        result.array_dimensions = dimensions;
        return result;
    }

    char peek() const noexcept {
        return position_ < input_.size() ? input_[position_] : '\0';
    }

    char take() {
        if (position_ >= input_.size()) fail("unexpected end of descriptor");
        return input_[position_++];
    }

    void expect(char expected) {
        if (take() != expected) fail(std::string("expected '") + expected + "'");
    }

    bool done() const noexcept { return position_ == input_.size(); }

private:
    [[noreturn]] void fail(const std::string& reason) const {
        throw DescriptorError(reason + " at descriptor offset " + std::to_string(position_));
    }

    std::string_view input_;
    std::size_t position_{};
};

} // namespace

JvmType parse_field_descriptor(std::string_view descriptor) {
    Parser parser(descriptor);
    auto result = parser.type(false);
    if (!parser.done()) {
        throw DescriptorError("trailing characters in field descriptor");
    }
    return result;
}

MethodDescriptor parse_method_descriptor(std::string_view descriptor) {
    Parser parser(descriptor);
    parser.expect('(');
    MethodDescriptor result;
    while (parser.peek() != ')') {
        if (parser.peek() == '\0') {
            throw DescriptorError("method descriptor is missing closing ')'");
        }
        result.parameters.push_back(parser.type(false));
    }
    parser.expect(')');
    result.return_type = parser.type(true);
    if (!parser.done()) {
        throw DescriptorError("trailing characters in method descriptor");
    }
    return result;
}


unsigned type_slot_width(const JvmType& type) {
    if (type.array_dimensions != 0) return 1;
    switch (type.kind) {
    case TypeKind::void_type: return 0;
    case TypeKind::long_type:
    case TypeKind::double_type: return 2;
    default: return 1;
    }
}

unsigned method_parameter_slots(const MethodDescriptor& descriptor, bool include_receiver) {
    unsigned slots = include_receiver ? 1U : 0U;
    for (const auto& parameter : descriptor.parameters) {
        slots += type_slot_width(parameter);
    }
    return slots;
}

void validate_method_parameter_slots(const MethodDescriptor& descriptor, bool include_receiver) {
    const unsigned slots = method_parameter_slots(descriptor, include_receiver);
    if (slots > 255U) {
        throw DescriptorError("method parameter slots exceed JVM limit of 255");
    }
}


std::string cpp_type_name(const JvmType& type) {
    if (type.array_dimensions != 0) return "mcnative::jvm::JArray";
    switch (type.kind) {
    case TypeKind::byte_type: return "std::int8_t";
    case TypeKind::char_type: return "char16_t";
    case TypeKind::double_type: return "double";
    case TypeKind::float_type: return "float";
    case TypeKind::int_type: return "std::int32_t";
    case TypeKind::long_type: return "std::int64_t";
    case TypeKind::short_type: return "std::int16_t";
    case TypeKind::boolean_type: return "bool";
    case TypeKind::void_type: return "void";
    case TypeKind::object_type: return "mcnative::jvm::JObject";
    }
    throw DescriptorError("unknown JVM type cannot be mapped to C++");
}

std::string generate_cpp_method_signature(std::string_view method_name,
                                          const MethodDescriptor& descriptor,
                                          bool is_static) {
    if (method_name.empty()) throw DescriptorError("C++ method name cannot be empty");
    validate_method_parameter_slots(descriptor, !is_static);
    std::string identifier;
    identifier.reserve(method_name.size() + 1);
    for (const unsigned char ch : method_name) {
        identifier.push_back((std::isalnum(ch) || ch == '_') ? static_cast<char>(ch) : '_');
    }
    if (identifier.empty() || std::isdigit(static_cast<unsigned char>(identifier.front())))
        identifier.insert(identifier.begin(), '_');

    std::ostringstream out;
    out << cpp_type_name(descriptor.return_type) << ' ' << identifier << '(';
    for (std::size_t i = 0; i < descriptor.parameters.size(); ++i) {
        if (i != 0) out << ", ";
        out << cpp_type_name(descriptor.parameters[i]) << " arg" << i;
    }
    out << ')';
    return out.str();
}

std::vector<std::uint16_t> method_parameter_local_indices(
    const MethodDescriptor& descriptor, bool is_static) {
    validate_method_parameter_slots(descriptor, !is_static);
    unsigned slot = is_static ? 0U : 1U;
    std::vector<std::uint16_t> result;
    result.reserve(descriptor.parameters.size());
    for (const auto& parameter : descriptor.parameters) {
        if (slot > 65535U) throw DescriptorError("parameter local index exceeds JVM limit");
        result.push_back(static_cast<std::uint16_t>(slot));
        slot += type_slot_width(parameter);
    }
    return result;
}

} // namespace mcnative::jvm
