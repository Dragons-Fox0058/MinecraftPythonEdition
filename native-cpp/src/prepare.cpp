#include "mcnative/prepare.hpp"

#include <array>
#include <bit>
#include <fstream>
#include <iomanip>
#include <regex>
#include <sstream>
#include <vector>

namespace mcnative {
namespace {

std::string read_text(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw PrepareError("cannot open " + path.string());
    std::ostringstream data;
    data << input.rdbuf();
    if (!input.good() && !input.eof()) throw PrepareError("cannot read " + path.string());
    return data.str();
}

std::string json_escape(const std::string& value) {
    std::ostringstream out;
    for (const unsigned char ch : value) {
        switch (ch) {
        case '"': out << "\\\""; break;
        case '\\': out << "\\\\"; break;
        case '\n': out << "\\n"; break;
        case '\r': out << "\\r"; break;
        case '\t': out << "\\t"; break;
        default:
            if (ch < 0x20U) out << '?';
            else out << static_cast<char>(ch);
        }
    }
    return out.str();
}

std::string client_download_object(const std::string& json) {
    const std::regex client_pattern(R"("client"\s*:\s*\{([^}]*)\})");
    std::smatch match;
    if (!std::regex_search(json, match, client_pattern)) {
        throw PrepareError("version JSON has no downloads.client object");
    }
    return match[1].str();
}

std::string required_string(const std::string& object, const std::string& key) {
    const std::regex pattern = std::regex("\"" + key + "\"\\s*:\\s*\"([0-9a-fA-F]+)\"");
    std::smatch match;
    if (!std::regex_search(object, match, pattern)) {
        throw PrepareError("version JSON downloads.client is missing " + key);
    }
    return match[1].str();
}

std::uint64_t required_size(const std::string& object) {
    const std::regex pattern(R"("size"\s*:\s*([0-9]+))");
    std::smatch match;
    if (!std::regex_search(object, match, pattern)) {
        throw PrepareError("version JSON downloads.client is missing size");
    }
    try {
        return std::stoull(match[1].str());
    } catch (...) {
        throw PrepareError("invalid client JAR size in version JSON");
    }
}

std::string sha1_bytes(const std::vector<std::uint8_t>& input) {
    std::vector<std::uint8_t> data = input;
    const std::uint64_t bit_length = static_cast<std::uint64_t>(data.size()) * 8U;
    data.push_back(0x80U);
    while ((data.size() % 64U) != 56U) data.push_back(0U);
    for (int shift = 56; shift >= 0; shift -= 8) {
        data.push_back(static_cast<std::uint8_t>(bit_length >> shift));
    }

    std::uint32_t h0 = 0x67452301U;
    std::uint32_t h1 = 0xEFCDAB89U;
    std::uint32_t h2 = 0x98BADCFEU;
    std::uint32_t h3 = 0x10325476U;
    std::uint32_t h4 = 0xC3D2E1F0U;

    for (std::size_t offset = 0; offset < data.size(); offset += 64U) {
        std::array<std::uint32_t, 80> words{};
        for (std::size_t i = 0; i < 16; ++i) {
            const auto p = offset + i * 4U;
            words[i] = (static_cast<std::uint32_t>(data[p]) << 24U) |
                       (static_cast<std::uint32_t>(data[p + 1]) << 16U) |
                       (static_cast<std::uint32_t>(data[p + 2]) << 8U) |
                       static_cast<std::uint32_t>(data[p + 3]);
        }
        for (std::size_t i = 16; i < 80; ++i) {
            words[i] = std::rotl(words[i - 3] ^ words[i - 8] ^ words[i - 14] ^ words[i - 16], 1);
        }

        std::uint32_t a = h0, b = h1, c = h2, d = h3, e = h4;
        for (std::size_t i = 0; i < 80; ++i) {
            std::uint32_t f = 0, k = 0;
            if (i < 20) { f = (b & c) | ((~b) & d); k = 0x5A827999U; }
            else if (i < 40) { f = b ^ c ^ d; k = 0x6ED9EBA1U; }
            else if (i < 60) { f = (b & c) | (b & d) | (c & d); k = 0x8F1BBCDCU; }
            else { f = b ^ c ^ d; k = 0xCA62C1D6U; }
            const auto temp = std::rotl(a, 5) + f + e + k + words[i];
            e = d; d = c; c = std::rotl(b, 30); b = a; a = temp;
        }
        h0 += a; h1 += b; h2 += c; h3 += d; h4 += e;
    }

    std::ostringstream out;
    out << std::hex << std::setfill('0')
        << std::setw(8) << h0 << std::setw(8) << h1 << std::setw(8) << h2
        << std::setw(8) << h3 << std::setw(8) << h4;
    return out.str();
}

} // namespace

std::string sha1_file(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw PrepareError("cannot open " + path.string());
    std::vector<std::uint8_t> bytes;
    std::array<char, 64 * 1024> buffer{};
    while (input) {
        input.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
        const auto count = input.gcount();
        bytes.insert(bytes.end(), buffer.data(), buffer.data() + count);
    }
    if (!input.eof()) throw PrepareError("cannot read " + path.string());
    return sha1_bytes(bytes);
}

PrepareResult prepare_minecraft_26_3(const std::filesystem::path& minecraft_dir,
                                     const std::filesystem::path& output_dir) {
    const auto version_dir = minecraft_dir / "versions" / "26.3";
    const auto version_json = version_dir / "26.3.json";
    const auto client_jar = version_dir / "26.3.jar";
    const auto libraries = minecraft_dir / "libraries";
    const auto assets = minecraft_dir / "assets";

    if (!std::filesystem::is_regular_file(version_json)) {
        throw PrepareError("Minecraft 26.3 version JSON was not found: " + version_json.string());
    }
    if (!std::filesystem::is_regular_file(client_jar)) {
        throw PrepareError("Minecraft 26.3 client JAR was not found: " + client_jar.string());
    }
    if (!std::filesystem::is_directory(libraries)) {
        throw PrepareError("Minecraft libraries directory was not found: " + libraries.string());
    }
    if (!std::filesystem::is_directory(assets)) {
        throw PrepareError("Minecraft assets directory was not found: " + assets.string());
    }

    const auto json = read_text(version_json);
    if (!std::regex_search(json, std::regex(R"("id"\s*:\s*"26\.3")"))) {
        throw PrepareError("version JSON does not identify Minecraft 26.3");
    }
    const auto client = client_download_object(json);
    const auto expected_sha1 = required_string(client, "sha1");
    const auto expected_size = required_size(client);
    const auto actual_size = std::filesystem::file_size(client_jar);
    if (actual_size != expected_size) {
        throw PrepareError("client JAR size mismatch: expected " + std::to_string(expected_size) +
                           ", found " + std::to_string(actual_size));
    }
    const auto actual_sha1 = sha1_file(client_jar);
    if (actual_sha1 != expected_sha1) {
        throw PrepareError("client JAR SHA-1 mismatch; use an unmodified official 26.3 installation");
    }

    std::filesystem::create_directories(output_dir);
    const auto manifest_path = output_dir / "prepare-manifest.json";
    std::ofstream manifest(manifest_path, std::ios::binary | std::ios::trunc);
    if (!manifest) throw PrepareError("cannot create " + manifest_path.string());
    manifest << "{\n"
             << "  \"schema\": 1,\n"
             << "  \"game\": \"Minecraft Java Edition\",\n"
             << "  \"version\": \"26.3\",\n"
             << "  \"preparation_mode\": \"verified-local-inputs\",\n"
             << "  \"game_files_copied\": false,\n"
             << "  \"client_jar\": \"" << json_escape(std::filesystem::absolute(client_jar).string()) << "\",\n"
             << "  \"version_json\": \"" << json_escape(std::filesystem::absolute(version_json).string()) << "\",\n"
             << "  \"client_jar_size\": " << actual_size << ",\n"
             << "  \"client_jar_sha1\": \"" << actual_sha1 << "\"\n"
             << "}\n";
    manifest.flush();
    if (!manifest) throw PrepareError("failed writing preparation manifest");

    return {client_jar, version_json, manifest_path, actual_size, actual_sha1};
}

} // namespace mcnative
