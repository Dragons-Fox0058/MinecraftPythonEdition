#include "mcnative/prepare.hpp"

#include <cassert>
#include <filesystem>
#include <fstream>
#include <string>

int main() {
    const auto root = std::filesystem::temp_directory_path() / "mcnative-prepare-test";
    std::filesystem::remove_all(root);
    const auto game = root / "game";
    const auto version = game / "versions" / "26.3";
    const auto output = root / "prepared";
    std::filesystem::create_directories(version);
    std::filesystem::create_directories(game / "libraries");
    std::filesystem::create_directories(game / "assets");

    {
        std::ofstream jar(version / "26.3.jar", std::ios::binary);
        jar << "abc";
    }
    {
        std::ofstream json(version / "26.3.json", std::ios::binary);
        json << R"({"id":"26.3","downloads":{"client":{"sha1":"a9993e364706816aba3e25717850c26c9cd0d89d","size":3,"url":"https://example.invalid/client.jar"}}})";
    }

    assert(mcnative::sha1_file(version / "26.3.jar") ==
           "a9993e364706816aba3e25717850c26c9cd0d89d");
    const auto result = mcnative::prepare_minecraft_26_3(game, output);
    assert(result.client_jar_size == 3);
    assert(result.client_jar_sha1 == "a9993e364706816aba3e25717850c26c9cd0d89d");
    assert(std::filesystem::is_regular_file(result.output_manifest));
    assert(!std::filesystem::exists(output / "26.3.jar"));

    {
        std::ofstream jar(version / "26.3.jar", std::ios::binary | std::ios::trunc);
        jar << "tampered";
    }
    bool rejected = false;
    try {
        (void)mcnative::prepare_minecraft_26_3(game, output);
    } catch (const mcnative::PrepareError&) {
        rejected = true;
    }
    assert(rejected);
    std::filesystem::remove_all(root);
    return 0;
}
