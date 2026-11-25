#include "mcnative/class_file.hpp"
#include "mcnative/codegen.hpp"
#include "mcnative/descriptor.hpp"
#include "mcnative/version.hpp"
#include "mcnative/prepare.hpp"

#include <exception>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string_view>
#include <vector>

namespace {

int inspect_class(const char* path) {
    const auto file = mcnative::jvm::ClassFileParser::parse_file(path);

    std::cout << "Class: " << file.this_name() << '\n'
              << "Super: " << (file.super_name().empty() ? "<none>" : file.super_name()) << '\n'
              << "Class-file version: " << file.major_version << '.' << file.minor_version << '\n'
              << "Constant-pool entries: " << (file.constant_pool.size() - 1) << '\n'
              << "Interfaces: " << file.interfaces.size() << '\n'
              << "Fields: " << file.fields.size() << '\n'
              << "Methods: " << file.methods.size() << "\n\n";

    for (const auto& method : file.methods) {
        const auto name = file.utf8(method.name_index);
        const auto descriptor = file.utf8(method.descriptor_index);
        const mcnative::jvm::CodeAttribute* code = nullptr;
        for (const auto& attribute : method.attributes) {
            if (attribute.code) {
                code = &*attribute.code;
                break;
            }
        }
        std::cout << "  " << name << descriptor;
        if (code != nullptr) {
            const auto instructions = mcnative::jvm::decode_bytecode(code->bytecode);
            std::cout << "  [" << code->bytecode.size() << " bytes, "
                      << instructions.size() << " instructions]";
        }
        std::cout << '\n';
    }
    return 0;
}

std::vector<std::uint8_t> parse_hex_bytecode(std::string_view hex) {
    if (hex.empty() || (hex.size() % 2) != 0) {
        throw std::invalid_argument("bytecode hex must contain a non-empty even number of digits");
    }
    std::vector<std::uint8_t> bytes;
    bytes.reserve(hex.size() / 2);
    for (std::size_t i = 0; i < hex.size(); i += 2) {
        unsigned value = 0;
        std::istringstream part{std::string(hex.substr(i, 2))};
        part >> std::hex >> value;
        if (!part || !part.eof() || value > 0xFFU) {
            throw std::invalid_argument("invalid hexadecimal bytecode at character " + std::to_string(i));
        }
        bytes.push_back(static_cast<std::uint8_t>(value));
    }
    return bytes;
}

int translate_int(std::string_view hex) {
    std::cout << mcnative::jvm::generate_int_method_cpp(parse_hex_bytecode(hex));
    return 0;
}

int translate_class_method(const char* path, std::string_view method_name,
                          std::string_view descriptor) {
    const auto parsed_descriptor = mcnative::jvm::parse_method_descriptor(descriptor);
    if (!parsed_descriptor.parameters.empty() ||
        parsed_descriptor.return_type.kind != mcnative::jvm::TypeKind::int_type ||
        parsed_descriptor.return_type.array_dimensions != 0) {
        throw std::invalid_argument("translate-method currently supports only methods with descriptor ()I");
    }

    const auto file = mcnative::jvm::ClassFileParser::parse_file(path);
    for (const auto& method : file.methods) {
        if (file.utf8(method.name_index) != method_name ||
            file.utf8(method.descriptor_index) != descriptor) {
            continue;
        }
        for (const auto& attribute : method.attributes) {
            if (attribute.code) {
                std::cout << mcnative::jvm::generate_int_method_cpp(attribute.code->bytecode, attribute.code->max_locals);
                return 0;
            }
        }
        throw std::invalid_argument("matching method has no Code attribute (it may be abstract or native)");
    }
    throw std::invalid_argument("method and descriptor were not found in the class file");
}


std::string csv_escape(std::string_view value) {
    std::string escaped = "\"";
    for (const char ch : value) {
        if (ch == '"') escaped += "\"\"";
        else escaped += ch;
    }
    escaped += '"';
    return escaped;
}

int index_classes(const std::filesystem::path& root, const std::filesystem::path& output_path) {
    if (!std::filesystem::is_directory(root)) {
        throw std::invalid_argument("class root is not a directory: " + root.string());
    }
    std::ofstream output(output_path, std::ios::binary);
    if (!output) {
        throw std::invalid_argument("cannot create index file: " + output_path.string());
    }
    output << "relative_path,internal_name,super_name,major,minor,interfaces,fields,methods,methods_with_code\n";

    std::size_t parsed = 0;
    std::size_t failed = 0;
    for (const auto& entry : std::filesystem::recursive_directory_iterator(root)) {
        if (!entry.is_regular_file() || entry.path().extension() != ".class") continue;
        try {
            const auto file = mcnative::jvm::ClassFileParser::parse_file(entry.path());
            std::size_t methods_with_code = 0;
            for (const auto& method : file.methods) {
                for (const auto& attribute : method.attributes) {
                    if (attribute.code) {
                        ++methods_with_code;
                        break;
                    }
                }
            }
            const auto relative = std::filesystem::relative(entry.path(), root).generic_string();
            output << csv_escape(relative) << ','
                   << csv_escape(file.this_name()) << ','
                   << csv_escape(file.super_name()) << ','
                   << file.major_version << ',' << file.minor_version << ','
                   << file.interfaces.size() << ',' << file.fields.size() << ','
                   << file.methods.size() << ',' << methods_with_code << '\n';
            ++parsed;
        } catch (const std::exception& error) {
            ++failed;
            std::cerr << "warning: " << entry.path().string() << ": " << error.what() << '\n';
        }
    }
    output.flush();
    if (!output) {
        throw std::runtime_error("failed while writing class index: " + output_path.string());
    }
    std::cout << "Indexed " << parsed << " class files; " << failed
              << " failed. Output: " << output_path.string() << '\n';
    return failed == 0 ? 0 : 1;
}


int prepare_installation(const std::filesystem::path& minecraft_dir,
                         const std::filesystem::path& output_dir) {
    const auto result = mcnative::prepare_minecraft_26_3(minecraft_dir, output_dir);
    std::cout << "Verified Minecraft Java Edition 26.3 inputs.\\n"
              << "Client JAR: " << result.client_jar << '\\n'
              << "Size: " << result.client_jar_size << " bytes\\n"
              << "SHA-1: " << result.client_jar_sha1 << '\\n'
              << "Local manifest: " << result.output_manifest << '\\n'
              << "No game files were copied or modified.\\n";
    return 0;
}

void print_usage() {
    std::cout << "Minecraft C++ Native — target Java Edition "
              << mcnative::target_game_version() << "\n\n"
              << "Usage:\n"
              << "  mc-native-tool --version\n"
              << "  mc-native-tool inspect-class <path-to-class-file>\n"
              << "  mc-native-tool translate-int <hex-bytecode>\n"
              << "  mc-native-tool translate-method <class-file> <method-name> <descriptor>\n"
              << "  mc-native-tool index-classes <extracted-classes-directory> <output.csv>\n"\n              << "  mc-native-tool prepare <minecraft-dir> <output-dir>\n";
}

} // namespace

int main(int argc, char** argv) {
    try {
        if (argc > 1 && std::string_view{argv[1]} == "--version") {
            std::cout << mcnative::project_name() << " — target Minecraft Java "
                      << mcnative::target_game_version() << " ("
                      << mcnative::cpp_standard() << ")\n";
            return 0;
        }

        if (argc == 3 && std::string_view{argv[1]} == "inspect-class") {
            return inspect_class(argv[2]);
        }
        if (argc == 3 && std::string_view{argv[1]} == "translate-int") {
            return translate_int(argv[2]);
        }
        if (argc == 5 && std::string_view{argv[1]} == "translate-method") {
            return translate_class_method(argv[2], argv[3], argv[4]);
        }
        if (argc == 4 && std::string_view{argv[1]} == "index-classes") {
            return index_classes(argv[2], argv[3]);
        }
        if (argc == 4 && std::string_view{argv[1]} == "prepare") {
            return prepare_installation(argv[2], argv[3]);
        }

        print_usage();
        return argc == 1 ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
