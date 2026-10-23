#include "memory_mapped_file.h"
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <utility>

MemoryMappedFile::MemoryMappedFile(const std::filesystem::path& path) { open(path); }
MemoryMappedFile::~MemoryMappedFile() { close(); }
MemoryMappedFile::MemoryMappedFile(MemoryMappedFile&& other) noexcept
    : fileHandle(std::exchange(other.fileHandle, -1)),
      fileView(std::exchange(other.fileView, MAP_FAILED)),
      fileSize(std::exchange(other.fileSize, 0)) {}

bool MemoryMappedFile::open(const std::filesystem::path& path) {
    close();
    fileHandle = ::open(path.c_str(), O_RDONLY | O_CLOEXEC);
    if (fileHandle < 0) {
        std::fprintf(stderr, "open %s: %s\n", path.c_str(), std::strerror(errno));
        return false;
    }
    struct stat info{};
    if (::fstat(fileHandle, &info) < 0 || !S_ISREG(info.st_mode) || info.st_size <= 0) {
        std::fprintf(stderr, "Not a readable nonempty regular file: %s\n", path.c_str());
        close(); return false;
    }
    fileSize = info.st_size;
    fileView = ::mmap(nullptr, static_cast<size_t>(fileSize), PROT_READ, MAP_PRIVATE, fileHandle, 0);
    if (fileView == MAP_FAILED) {
        std::fprintf(stderr, "mmap %s: %s\n", path.c_str(), std::strerror(errno));
        close(); return false;
    }
    return true;
}
void MemoryMappedFile::close() {
    if (fileView != MAP_FAILED) ::munmap(fileView, static_cast<size_t>(fileSize));
    if (fileHandle >= 0) ::close(fileHandle);
    fileView = MAP_FAILED; fileHandle = -1; fileSize = 0;
}
bool MemoryMappedFile::isOpen() const { return fileView != MAP_FAILED; }
uint8_t* MemoryMappedFile::data() const { return static_cast<uint8_t*>(fileView); }
size_t MemoryMappedFile::size() const { return static_cast<size_t>(fileSize); }
