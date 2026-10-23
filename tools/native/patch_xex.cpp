#include "xex_patcher.h"
#include <cstdio>
#include <filesystem>

int main(int argc, char** argv) {
    if (argc != 4) {
        std::fprintf(stderr, "usage: ttt2_patch_xex <base.xex> <update.xexp> <new-output.xex>\n");
        return 2;
    }
    if (std::filesystem::exists(argv[3])) {
        std::fprintf(stderr, "Refusing to overwrite output: %s\n", argv[3]);
        return 2;
    }
    const auto result = XexPatcher::apply(argv[1], argv[2], argv[3]);
    if (result != XexPatcher::Result::Success) {
        std::fprintf(stderr, "XEX patch failed (code %d)\n", static_cast<int>(result));
        return 1;
    }
    return 0;
}
