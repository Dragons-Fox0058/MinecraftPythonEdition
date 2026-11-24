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
    return 0;
}
