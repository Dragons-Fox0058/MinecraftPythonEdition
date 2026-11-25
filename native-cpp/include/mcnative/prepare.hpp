#pragma once

#include <cstdint>
#include <filesystem>
#include <stdexcept>
#include <string>

namespace mcnative {

class PrepareError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

struct PrepareResult {
    std::filesystem::path client_jar;
    std::filesystem::path version_json;
    std::filesystem::path output_manifest;
    std::uint64_t client_jar_size{};
    std::string client_jar_sha1;
};

// Validates a user's existing official-launcher installation and writes only a local
// metadata manifest. Game binaries and assets are never copied into the repository.
[[nodiscard]] PrepareResult prepare_minecraft_26_3(
    const std::filesystem::path& minecraft_dir,
    const std::filesystem::path& output_dir);

[[nodiscard]] std::string sha1_file(const std::filesystem::path& path);

} // namespace mcnative
