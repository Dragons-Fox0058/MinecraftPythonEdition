#include "mcnative/descriptor.hpp"

#include <cassert>

using namespace mcnative::jvm;

int main() {
    const auto field = parse_field_descriptor("[[Ljava/lang/String;");
    assert(field.kind == TypeKind::object_type);
    assert(field.class_name == "java/lang/String");
    assert(field.array_dimensions == 2);

    const auto method = parse_method_descriptor("(IJLjava/lang/Object;[B)D");
    assert(method.parameters.size() == 4);
    assert(method.parameters[0].kind == TypeKind::int_type);
    assert(method.parameters[1].kind == TypeKind::long_type);
    assert(method.parameters[2].class_name == "java/lang/Object");
    assert(method.parameters[3].kind == TypeKind::byte_type);
    assert(method.parameters[3].array_dimensions == 1);
    assert(method.return_type.kind == TypeKind::double_type);

    const auto ctor = parse_method_descriptor("()V");
    assert(ctor.parameters.empty());
    assert(ctor.return_type.kind == TypeKind::void_type);

    bool rejected = false;
    try {
        (void)parse_field_descriptor("V");
    } catch (const DescriptorError&) {
        rejected = true;
    }
    assert(rejected);

    rejected = false;
    try {
        (void)parse_method_descriptor("(I)Vjunk");
    } catch (const DescriptorError&) {
        rejected = true;
    }
    assert(rejected);
    assert(type_slot_width(method.parameters[0]) == 1);
    assert(type_slot_width(method.parameters[1]) == 2);
    assert(type_slot_width(method.parameters[2]) == 1);
    assert(method_parameter_slots(method) == 5);
    assert(method_parameter_slots(method, true) == 6);
    assert(type_slot_width(method.return_type) == 2);
    assert(type_slot_width(ctor.return_type) == 0);

    const auto arrays = parse_method_descriptor("([J[D[[I)J");
    assert(method_parameter_slots(arrays) == 3);
    assert(type_slot_width(arrays.return_type) == 2);

    std::string max_static_descriptor = "(" + std::string(255, 'I') + ")V";
    const auto max_static = parse_method_descriptor(max_static_descriptor);
    assert(method_parameter_slots(max_static) == 255);
    validate_method_parameter_slots(max_static);
    rejected = false;
    try {
        validate_method_parameter_slots(max_static, true);
    } catch (const DescriptorError&) {
        rejected = true;
    }
    assert(rejected);

    const auto too_many = parse_method_descriptor("(" + std::string(256, 'I') + ")V");
    rejected = false;
    try {
        validate_method_parameter_slots(too_many);
    } catch (const DescriptorError&) {
        rejected = true;
    }
    assert(rejected);

    const auto wide_boundary = parse_method_descriptor("(" + std::string(126, 'J') + "I)V");
    assert(method_parameter_slots(wide_boundary) == 253);
    validate_method_parameter_slots(wide_boundary, true);


    const auto abi = parse_method_descriptor("(IDLjava/lang/String;[J)Ljava/lang/Object;");
    assert(cpp_type_name(abi.parameters[0]) == "std::int32_t");
    assert(cpp_type_name(abi.parameters[1]) == "double");
    assert(cpp_type_name(abi.parameters[2]) == "mcnative::jvm::JObject");
    assert(cpp_type_name(abi.parameters[3]) == "mcnative::jvm::JArray");
    assert(generate_cpp_method_signature("calculate-value", abi) ==
           "mcnative::jvm::JObject calculate_value(std::int32_t arg0, double arg1, mcnative::jvm::JObject arg2, mcnative::jvm::JArray arg3)");
    const auto static_slots = method_parameter_local_indices(abi, true);
    assert((static_slots == std::vector<std::uint16_t>{0, 1, 3, 4}));
    const auto instance_slots = method_parameter_local_indices(abi, false);
    assert((instance_slots == std::vector<std::uint16_t>{1, 2, 4, 5}));

    return 0;
}
