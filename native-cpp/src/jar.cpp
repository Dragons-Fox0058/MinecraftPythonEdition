#include "mcnative/jar.hpp"

#include <zlib.h>

#include <algorithm>
#include <array>
#include <fstream>
#include <limits>
#include <string_view>
#include <vector>

namespace mcnative {
namespace {

constexpr std::uint32_t eocd_signature = 0x06054b50U;
constexpr std::uint32_t central_signature = 0x02014b50U;
constexpr std::uint32_t local_signature = 0x04034b50U;
constexpr std::uint64_t max_class_size = 64ULL * 1024ULL * 1024ULL;
constexpr std::uint64_t max_total_size = 2ULL * 1024ULL * 1024ULL * 1024ULL;

std::uint16_t u16(const std::vector<std::uint8_t>& b, std::size_t p) {
    if (p > b.size() || b.size() - p < 2) throw JarError("truncated ZIP 16-bit field");
    return static_cast<std::uint16_t>(b[p] | (static_cast<std::uint16_t>(b[p + 1]) << 8U));
}
std::uint32_t u32(const std::vector<std::uint8_t>& b, std::size_t p) {
    if (p > b.size() || b.size() - p < 4) throw JarError("truncated ZIP 32-bit field");
    return static_cast<std::uint32_t>(b[p]) |
           (static_cast<std::uint32_t>(b[p + 1]) << 8U) |
           (static_cast<std::uint32_t>(b[p + 2]) << 16U) |
           (static_cast<std::uint32_t>(b[p + 3]) << 24U);
}
void require_range(const std::vector<std::uint8_t>& b, std::uint64_t p, std::uint64_t n) {
    if (p > b.size() || n > b.size() - static_cast<std::size_t>(p))
        throw JarError("ZIP record points outside the archive");
}
std::vector<std::uint8_t> read_file(const std::filesystem::path& path) {
    std::ifstream in(path, std::ios::binary | std::ios::ate);
    if (!in) throw JarError("cannot open JAR: " + path.string());
    const auto end = in.tellg();
    if (end < 0) throw JarError("cannot determine JAR size");
    if (static_cast<std::uint64_t>(end) > std::numeric_limits<std::size_t>::max())
        throw JarError("JAR is too large for this process");
    std::vector<std::uint8_t> data(static_cast<std::size_t>(end));
    in.seekg(0);
    if (!data.empty()) in.read(reinterpret_cast<char*>(data.data()), static_cast<std::streamsize>(data.size()));
    if (!in) throw JarError("failed reading JAR");
    return data;
}
bool safe_class_path(std::string_view name) {
    if (name.empty() || name.front() == '/' || name.find('\\') != std::string_view::npos ||
        name.find(':') != std::string_view::npos) return false;
    std::size_t start = 0;
    while (start <= name.size()) {
        const auto end = name.find('/', start);
        const auto part = name.substr(start, end == std::string_view::npos ? name.size() - start : end - start);
        if (part == ".." || part == "." || part.empty()) return false;
        if (end == std::string_view::npos) break;
        start = end + 1;
    }
    return name.ends_with(".class");
}
std::vector<std::uint8_t> inflate_raw(const std::uint8_t* input, std::size_t input_size,
                                      std::size_t output_size) {
    std::vector<std::uint8_t> output(output_size);
    z_stream stream{};
    stream.next_in = const_cast<Bytef*>(reinterpret_cast<const Bytef*>(input));
    stream.avail_in = static_cast<uInt>(input_size);
    stream.next_out = reinterpret_cast<Bytef*>(output.data());
    stream.avail_out = static_cast<uInt>(output.size());
    if (input_size > std::numeric_limits<uInt>::max() || output_size > std::numeric_limits<uInt>::max())
        throw JarError("individual class entry exceeds zlib limits");
    if (inflateInit2(&stream, -MAX_WBITS) != Z_OK) throw JarError("could not initialize DEFLATE decoder");
    const int status = inflate(&stream, Z_FINISH);
    inflateEnd(&stream);
    if (status != Z_STREAM_END || stream.total_out != output_size)
        throw JarError("invalid or truncated DEFLATE class entry");
    return output;
}
std::vector<std::uint8_t> decode_entry(const std::vector<std::uint8_t>& archive,
                                       std::uint32_t local_offset, std::uint16_t expected_method,
                                       std::uint32_t compressed_size, std::uint32_t uncompressed_size,
                                       std::uint32_t expected_crc) {
    require_range(archive, local_offset, 30);
    if (u32(archive, local_offset) != local_signature) throw JarError("invalid local ZIP header signature");
    const auto flags = u16(archive, local_offset + 6);
    const auto method = u16(archive, local_offset + 8);
    const auto name_len = u16(archive, local_offset + 26);
    const auto extra_len = u16(archive, local_offset + 28);
    if ((flags & 1U) != 0) throw JarError("encrypted JAR entries are not supported");
    if (method != expected_method) throw JarError("local and central ZIP compression methods differ");
    const std::uint64_t data_offset = static_cast<std::uint64_t>(local_offset) + 30U + name_len + extra_len;
    require_range(archive, data_offset, compressed_size);
    std::vector<std::uint8_t> result;
    if (method == 0) {
        if (compressed_size != uncompressed_size) throw JarError("stored ZIP entry has inconsistent sizes");
        result.assign(archive.begin() + static_cast<std::ptrdiff_t>(data_offset),
                      archive.begin() + static_cast<std::ptrdiff_t>(data_offset + compressed_size));
    } else if (method == 8) {
        result = inflate_raw(archive.data() + data_offset, compressed_size, uncompressed_size);
    } else {
        throw JarError("unsupported ZIP compression method " + std::to_string(method));
    }
    const auto crc = crc32(0L, reinterpret_cast<const Bytef*>(result.data()), static_cast<uInt>(result.size()));
    if (static_cast<std::uint32_t>(crc) != expected_crc) throw JarError("JAR class entry CRC-32 mismatch");
    return result;
}

} // namespace

JarExtractionResult extract_jar_classes(const std::filesystem::path& jar_path,
                                        const std::filesystem::path& output_directory) {
    const auto archive = read_file(jar_path);
    if (archive.size() < 22) throw JarError("file is too small to be a ZIP/JAR archive");
    const std::size_t search_begin = archive.size() > 65557U ? archive.size() - 65557U : 0U;
    std::size_t eocd = std::string::npos;
    for (std::size_t p = archive.size() - 22U;; --p) {
        if (u32(archive, p) == eocd_signature) { eocd = p; break; }
        if (p == search_begin) break;
    }
    if (eocd == std::string::npos) throw JarError("ZIP end-of-central-directory record was not found");
    if (u16(archive, eocd + 4) != 0 || u16(archive, eocd + 6) != 0)
        throw JarError("multi-disk ZIP archives are not supported");
    const auto disk_entries = u16(archive, eocd + 8);
    const auto total_entries = u16(archive, eocd + 10);
    const auto central_size = u32(archive, eocd + 12);
    const auto central_offset = u32(archive, eocd + 16);
    if (disk_entries != total_entries || total_entries == 0xffffU ||
        central_size == 0xffffffffU || central_offset == 0xffffffffU)
        throw JarError("ZIP64 or inconsistent central directory is not supported");
    require_range(archive, central_offset, central_size);
    if (static_cast<std::uint64_t>(central_offset) + central_size > eocd)
        throw JarError("central directory overlaps ZIP trailer");

    std::filesystem::create_directories(output_directory);
    std::size_t cursor = central_offset;
    std::uint64_t count = 0, total_bytes = 0;
    for (std::uint32_t i = 0; i < total_entries; ++i) {
        require_range(archive, cursor, 46);
        if (u32(archive, cursor) != central_signature) throw JarError("invalid central-directory file header");
        const auto flags = u16(archive, cursor + 8);
        const auto method = u16(archive, cursor + 10);
        const auto crc = u32(archive, cursor + 16);
        const auto compressed = u32(archive, cursor + 20);
        const auto uncompressed = u32(archive, cursor + 24);
        const auto name_len = u16(archive, cursor + 28);
        const auto extra_len = u16(archive, cursor + 30);
        const auto comment_len = u16(archive, cursor + 32);
        const auto disk_start = u16(archive, cursor + 34);
        const auto local_offset = u32(archive, cursor + 42);
        const std::uint64_t record_size = 46ULL + name_len + extra_len + comment_len;
        require_range(archive, cursor, record_size);
        const std::string name(reinterpret_cast<const char*>(archive.data() + cursor + 46), name_len);
        cursor += static_cast<std::size_t>(record_size);
        if (!name.ends_with(".class")) continue;
        if ((flags & 1U) != 0 || disk_start != 0) throw JarError("encrypted or split class entry is not supported");
        if (!safe_class_path(name)) throw JarError("unsafe class entry path: " + name);
        if (uncompressed > max_class_size || total_bytes + uncompressed > max_total_size)
            throw JarError("class extraction size limit exceeded");
        const auto bytes = decode_entry(archive, local_offset, method, compressed, uncompressed, crc);
        const auto destination = output_directory / std::filesystem::path(name);
        std::filesystem::create_directories(destination.parent_path());
        std::ofstream out(destination, std::ios::binary | std::ios::trunc);
        if (!out) throw JarError("cannot create extracted class: " + destination.string());
        if (!bytes.empty()) out.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
        if (!out) throw JarError("failed writing extracted class: " + destination.string());
        ++count;
        total_bytes += bytes.size();
    }
    if (cursor != static_cast<std::size_t>(central_offset) + central_size)
        throw JarError("central-directory size does not match its entries");
    return {count, total_bytes, output_directory};
}

} // namespace mcnative
