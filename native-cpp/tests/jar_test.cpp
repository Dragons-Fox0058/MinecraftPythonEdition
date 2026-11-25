#include "mcnative/jar.hpp"

#include <zlib.h>

#include <cassert>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

namespace {
void put16(std::vector<std::uint8_t>& b, std::uint16_t v) {
    b.push_back(static_cast<std::uint8_t>(v));
    b.push_back(static_cast<std::uint8_t>(v >> 8U));
}
void put32(std::vector<std::uint8_t>& b, std::uint32_t v) {
    put16(b, static_cast<std::uint16_t>(v));
    put16(b, static_cast<std::uint16_t>(v >> 16U));
}
std::vector<std::uint8_t> make_zip(const std::string& name, const std::string& contents) {
    std::vector<std::uint8_t> b;
    const auto crc = static_cast<std::uint32_t>(crc32(0L,
        reinterpret_cast<const Bytef*>(contents.data()), static_cast<uInt>(contents.size())));
    put32(b, 0x04034b50U); put16(b, 20); put16(b, 0); put16(b, 0);
    put16(b, 0); put16(b, 0); put32(b, crc);
    put32(b, static_cast<std::uint32_t>(contents.size()));
    put32(b, static_cast<std::uint32_t>(contents.size()));
    put16(b, static_cast<std::uint16_t>(name.size())); put16(b, 0);
    b.insert(b.end(), name.begin(), name.end());
    b.insert(b.end(), contents.begin(), contents.end());

    const auto central_offset = static_cast<std::uint32_t>(b.size());
    put32(b, 0x02014b50U); put16(b, 20); put16(b, 20); put16(b, 0);
    put16(b, 0); put16(b, 0); put32(b, crc);
    put32(b, static_cast<std::uint32_t>(contents.size()));
    put32(b, static_cast<std::uint32_t>(contents.size()));
    put16(b, static_cast<std::uint16_t>(name.size())); put16(b, 0); put16(b, 0);
    put16(b, 0); put16(b, 0); put32(b, 0); put32(b, 0);
    b.insert(b.end(), name.begin(), name.end());
    const auto central_size = static_cast<std::uint32_t>(b.size()) - central_offset;
    put32(b, 0x06054b50U); put16(b, 0); put16(b, 0);
    put16(b, 1); put16(b, 1); put32(b, central_size); put32(b, central_offset); put16(b, 0);
    return b;
}
void write(const std::filesystem::path& path, const std::vector<std::uint8_t>& bytes) {
    std::ofstream out(path, std::ios::binary);
    out.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
}
}

int main() {
    const auto root = std::filesystem::temp_directory_path() / "mcnative-jar-test";
    std::filesystem::remove_all(root);
    std::filesystem::create_directories(root);
    const auto jar = root / "sample.jar";
    const std::string payload = "synthetic class bytes";
    write(jar, make_zip("example/Test.class", payload));

    const auto output = root / "classes";
    const auto result = mcnative::extract_jar_classes(jar, output);
    assert(result.class_files == 1);
    assert(result.uncompressed_bytes == payload.size());
    std::ifstream extracted(output / "example" / "Test.class", std::ios::binary);
    const std::string actual((std::istreambuf_iterator<char>(extracted)), {});
    assert(actual == payload);

    write(jar, make_zip("../escape.class", payload));
    bool rejected = false;
    try { (void)mcnative::extract_jar_classes(jar, root / "unsafe"); }
    catch (const mcnative::JarError&) { rejected = true; }
    assert(rejected);
    assert(!std::filesystem::exists(root / "escape.class"));
    std::filesystem::remove_all(root);
    return 0;
}
