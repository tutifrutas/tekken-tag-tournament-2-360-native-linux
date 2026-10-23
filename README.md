# Tekken Tag Tournament 2 — native Linux

A native Linux static recompilation of Xbox 360 Tekken Tag Tournament 2 TU3,
using [ReXGlue](https://github.com/tutifrutas/rexglue-sdk) and Vulkan.
No Wine or Proton is used. Online play is not supported.

**No game data, title updates, generated guest code, artwork or game binaries
are included.** Supply your own USA/Europe disc ISO and matching TU3 package in
a ZIP file. Data preparation verifies the disc executable, update package,
executable patch and patched executable before publishing the local game folder.
It does not download game files or modify your source ISO/ZIP.

This port is experimental. A successful build does not establish complete
menu, match, roster, save, audio or rendering correctness.

## Requirements

- Linux x86-64, Clang 18+, CMake 3.25+, Ninja, Git and Python 3.11+.
- The [SDK's build dependencies](https://github.com/tutifrutas/rexglue-sdk#requirements).
- Read/write access to `/dev/ntsync`; there is no POSIX fallback. Your kernel
  must provide NTSYNC and your user must have permission to open the device.
- A Vulkan 1.3 driver/device supporting `VK_EXT_fragment_shader_interlock`
  and the SDK's renderer feature checks. Wayland is the default display path.

Qt and KDE are not required to build the game.

## Prepare your game files

Clone the SDK and game as sibling directories:

```sh
git clone --recurse-submodules https://github.com/tutifrutas/rexglue-sdk.git
git clone https://github.com/tutifrutas/tekken-tag-tournament-2-360-native-linux.git
cd tekken-tag-tournament-2-360-native-linux
python3 tools/bootstrap_linux.py
cmake -S tools/native -B build/data-tools -G Ninja \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
cmake --build build/data-tools --parallel 8
python3 tools/prepare_linux_data.py --iso '/path/to/your-disc.iso' \
  --tu3 '/path/to/your-TU3.zip'
```

Bootstrap fetches a pinned [XenonRecomp](https://github.com/hedge-dev/XenonRecomp)
checkout for its native XEX patcher and LZX decompressor. Fetched sources retain
their upstream licenses and are ignored by Git.

Preparation creates `game/` and refuses to replace an existing directory or
symlink. TU3's `data100.bin` and `data100.ofs` belong in `game/update/`, not the
disc root. Required LZX archives are expanded locally. Leave this layout intact.
The manifest uses `game/default.xex`.

## Build and run

```sh
cmake -S . -B build/linux-vulkan -G Ninja \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_BUILD_TYPE=Release -DREXSDK_DIR="$PWD/../rexglue-sdk" \
  -DREXGLUE_USE_D3D12=OFF -DREXGLUE_USE_VULKAN=ON \
  -DREXGLUE_ENABLE_TRACY=OFF -DREXGLUE_ENABLE_PERF_COUNTERS=OFF \
  -DREXGLUE_RECOMP_DEBUG_INFO=none
cmake --build build/linux-vulkan --target ttt2_codegen --parallel 8
cmake -S . -B build/linux-vulkan
cmake --build build/linux-vulkan --target ttt2 --parallel 8
mkdir -p build/linux-vulkan/{user,cache,logs}
build/linux-vulkan/ttt2 --game_data_root="$PWD/game" \
  --user_data_root="$PWD/build/linux-vulkan/user" \
  --cache_root="$PWD/build/linux-vulkan/cache" \
  --log_file="$PWD/build/linux-vulkan/logs/game.log"
```

Code generation must precede the second configure step on a clean checkout.
The defaults are Wayland, Vulkan FSI/ROV and full resolve readback.
F11 toggles fullscreen; F3 shows rendering statistics.

The optional [KDE launcher](https://github.com/tutifrutas/tekken-360-kde-launcher)
is built separately. It expects `ttt2`, `librexruntime.so`, `librexgpu-xenos.so`
and `game/` in one installation folder. A development build can use a relative
symlink from `build/linux-vulkan/game` to `../../game`, only if that path does
not already exist. Never overwrite existing game data or saves.
**Do not redistribute a built installation or generated guest sources.**

## Tests

```sh
python3 tests/native/test_data_preparation.py
cmake -S tools/xdvdfs -B build/xdvdfs-tests -G Ninja -DTTT2_XDVDFS_TESTS=ON
cmake --build build/xdvdfs-tests
ctest --test-dir build/xdvdfs-tests --output-on-failure
ctest --test-dir build/linux-vulkan --output-on-failure
```

Game-dependent checks skip when your local data or generated sources are absent.
These checks do not launch the game or prove gameplay correctness.

## License and credits

Original contributions are [BSD-3-Clause](LICENSE). Inherited source has
separate licensing requirements; see [NOTICE](NOTICE). The original project is
[shihabal3amri/tekken-tag-tournament-2-pc](https://github.com/shihabal3amri/tekken-tag-tournament-2-pc).
ReXGlue derives from [Xenia](https://github.com/xenia-project/xenia).
Tekken and its game content belong to their respective owners. This independent
project is not affiliated with Bandai Namco or Microsoft and grants no rights
to the game.
