#pragma once

#include <cstdint>
#include <filesystem>
#include <stdexcept>
#include <string>

namespace mcnative {

class JarError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

struct JarExtractionResult {
    std::uint64_t class_files{};
    std::uint64_t uncompressed_bytes{};
    std::filesystem::path output_directory;
};

// Reads standard ZIP/JAR central-directory records and extracts only .class files.
// Supports stored and DEFLATE entries; rejects encrypted, ZIP64, and unsafe paths.
[[nodiscard]] JarExtractionResult extract_jar_classes(
    const std::filesystem::path& jar_path,
    const std::filesystem::path& output_directory);

} // namespace mcnative
