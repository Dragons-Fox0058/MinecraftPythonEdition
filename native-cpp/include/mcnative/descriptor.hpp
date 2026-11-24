#pragma once

#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace mcnative::jvm {

class DescriptorError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

enum class TypeKind {
    byte_type, char_type, double_type, float_type, int_type, long_type,
    short_type, boolean_type, void_type, object_type
};

struct JvmType {
    TypeKind kind{};
    std::string class_name; // populated only for object types; JVM internal name form
    unsigned array_dimensions{};
};

struct MethodDescriptor {
    std::vector<JvmType> parameters;
    JvmType return_type;
};

[[nodiscard]] JvmType parse_field_descriptor(std::string_view descriptor);
[[nodiscard]] MethodDescriptor parse_method_descriptor(std::string_view descriptor);

} // namespace mcnative::jvm
