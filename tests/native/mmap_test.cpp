#include "memory_mapped_file.h"
#include <fcntl.h>
#include <unistd.h>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <utility>

void require(bool value) { if (!value) { std::fputs("native mmap check failed\n", stderr); std::exit(1); } }
int main() {
    char pattern[] = "/tmp/t6-mmap-XXXXXX";
    char* directory = ::mkdtemp(pattern); require(directory != nullptr);
    const std::filesystem::path root(directory), file = root / "image", empty = root / "empty";
    { std::ofstream output(file); output << "native mapping"; }
    { std::ofstream output(empty); }
    {
        MemoryMappedFile first(file); require(first.isOpen() && first.size() == 14);
        require((::fcntl(first.fileHandle, F_GETFD) & FD_CLOEXEC) != 0);
        MemoryMappedFile second(std::move(first));
        require(!first.isOpen() && second.isOpen() && second.data()[0] == 'n');
        second.close(); second.close(); require(!second.isOpen() && second.size() == 0);
        const int unrelated = ::open("/dev/null", O_RDONLY | O_CLOEXEC); require(unrelated >= 0);
        second.close(); require(::fcntl(unrelated, F_GETFD) >= 0); ::close(unrelated);
        require(second.open(file)); require(second.open(file)); // reopen releases previous mapping
        require(!second.open(empty) && !second.isOpen());
        require(!second.open(root / "missing") && !second.isOpen());
        require(second.open(file));
    }
    std::filesystem::remove_all(root);
    std::puts("native mmap open/reopen/move/idempotent-close/failure checks passed");
}
