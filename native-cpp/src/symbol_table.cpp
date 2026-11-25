#include "mcnative/symbol_table.hpp"

#include <cctype>
#include <cstdint>
#include <iomanip>
#include <sstream>
#include <utility>

namespace mcnative::jvm {
namespace {

std::string sanitize(std::string_view value) {
    std::string result;
    result.reserve(value.size() + 1);
    for (const unsigned char ch : value) {
        result.push_back((std::isalnum(ch) || ch == '_') ? static_cast<char>(ch) : '_');
    }
    if (result.empty() || std::isdigit(static_cast<unsigned char>(result.front()))) {
        result.insert(result.begin(), '_');
    }
    return result;
}

std::uint64_t stable_hash(std::string_view value) {
    std::uint64_t hash = 14695981039346656037ULL;
    for (const unsigned char ch : value) {
        hash ^= ch;
        hash *= 1099511628211ULL;
    }
    return hash;
}

} // namespace

std::string cpp_class_namespace(std::string_view internal_name) {
    if (internal_name.empty()) {
        throw SymbolTableError("JVM class internal name cannot be empty");
    }
    return "C_" + sanitize(internal_name);
}

std::string cpp_method_symbol(std::string_view method_name, std::string_view descriptor) {
    if (method_name.empty() || descriptor.empty()) {
        throw SymbolTableError("JVM method name and descriptor cannot be empty");
    }
    std::string identity(method_name);
    identity.push_back('\0');
    identity.append(descriptor);
    std::ostringstream output;
    output << "M_" << sanitize(method_name) << "_D_" << std::hex << std::setfill('0')
           << std::setw(16) << stable_hash(identity);
    return output.str();
}

void SymbolTable::add_class(const ClassFile& class_file) {
    const auto owner = class_file.this_name();
    if (owner.empty()) throw SymbolTableError("cannot register a class with an empty internal name");
    if (classes_.contains(owner)) {
        throw SymbolTableError("duplicate JVM class definition: " + owner);
    }

    const auto namespace_name = cpp_class_namespace(owner);
    for (const auto& [existing_name, existing] : classes_) {
        if (existing.cpp_namespace == namespace_name) {
            throw SymbolTableError("C++ namespace collision between JVM classes: " +
                                   existing_name + " and " + owner);
        }
    }

    ClassSymbol symbol;
    symbol.internal_name = owner;
    symbol.cpp_namespace = namespace_name;

    for (const auto& method : class_file.methods) {
        const auto name = class_file.utf8(method.name_index);
        const auto descriptor = class_file.utf8(method.descriptor_index);
        for (const auto& existing : symbol.methods) {
            if (existing.name == name && existing.descriptor == descriptor) {
                throw SymbolTableError("duplicate JVM method definition: " + owner + "." +
                                       name + descriptor);
            }
        }
        bool has_code = false;
        for (const auto& attribute : method.attributes) {
            if (attribute.code) {
                has_code = true;
                break;
            }
        }
        symbol.methods.push_back(MethodSymbol{
            name, descriptor, cpp_method_symbol(name, descriptor),
            method.access_flags, has_code
        });
    }

    classes_.emplace(owner, std::move(symbol));
}

const ClassSymbol* SymbolTable::find_class(std::string_view internal_name) const {
    const auto it = classes_.find(internal_name);
    return it == classes_.end() ? nullptr : &it->second;
}

const MethodSymbol* SymbolTable::find_method(std::string_view owner,
                                             std::string_view name,
                                             std::string_view descriptor) const {
    const auto* klass = find_class(owner);
    if (klass == nullptr) return nullptr;
    for (const auto& method : klass->methods) {
        if (method.name == name && method.descriptor == descriptor) return &method;
    }
    return nullptr;
}

} // namespace mcnative::jvm
