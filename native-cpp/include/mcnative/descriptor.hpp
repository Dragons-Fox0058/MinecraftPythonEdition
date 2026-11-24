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
    std::string class_name;
    unsigned array_dimensions{};
};

struct MethodDescriptor {
    std::vector<JvmType> parameters;
    JvmType return_type;
};

[[nodiscard]] JvmType parse_field_descriptor(std::string_view descriptor);
[[nodiscard]] MethodDescriptor parse_method_descriptor(std::string_view descriptor);

// JVM local-variable/operand-stack slot width. Arrays and references occupy one slot.
[[nodiscard]] unsigned type_slot_width(const JvmType& type);
// Includes the receiver slot for non-static instance methods when requested.
[[nodiscard]] unsigned method_parameter_slots(const MethodDescriptor& descriptor,
                                              bool include_receiver = false);

} // namespace mcnative::jvm
