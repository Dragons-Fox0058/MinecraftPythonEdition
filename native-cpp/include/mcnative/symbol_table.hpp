#pragma once

#include "mcnative/class_file.hpp"

#include <map>
#include <string>
#include <string_view>
#include <vector>

namespace mcnative::jvm {

struct MethodSymbol {
    std::string name;
    std::string descriptor;
    std::string cpp_name;
    std::uint16_t access_flags{};
    bool has_code{};
};

struct ClassSymbol {
    std::string internal_name;
    std::string cpp_namespace;
    std::vector<MethodSymbol> methods;
};

class SymbolTableError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

// Stable names shared by the bytecode caller generator and class-level emitter.
[[nodiscard]] std::string cpp_class_namespace(std::string_view internal_name);
[[nodiscard]] std::string cpp_method_symbol(std::string_view method_name,
                                            std::string_view descriptor);

class SymbolTable {
public:
    // A class may be registered once. Duplicate method name+descriptor pairs are rejected.
    void add_class(const ClassFile& class_file);

    [[nodiscard]] const ClassSymbol* find_class(std::string_view internal_name) const;
    [[nodiscard]] const MethodSymbol* find_method(std::string_view owner,
                                                  std::string_view name,
                                                  std::string_view descriptor) const;
    [[nodiscard]] std::size_t class_count() const noexcept { return classes_.size(); }

private:
    std::map<std::string, ClassSymbol, std::less<>> classes_;
};

} // namespace mcnative::jvm
