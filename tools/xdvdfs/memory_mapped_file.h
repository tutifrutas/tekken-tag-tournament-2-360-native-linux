#pragma once
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <sys/mman.h>

struct MemoryMappedFile {
    int fileHandle = -1;
    void* fileView = MAP_FAILED;
    off_t fileSize = 0;

    MemoryMappedFile() = default;
    explicit MemoryMappedFile(const std::filesystem::path& path);
    MemoryMappedFile(MemoryMappedFile&& other) noexcept;
    MemoryMappedFile(const MemoryMappedFile&) = delete;
    MemoryMappedFile& operator=(const MemoryMappedFile&) = delete;
    ~MemoryMappedFile();

    bool open(const std::filesystem::path& path);
    void close();
    bool isOpen() const;
    uint8_t* data() const;
    size_t size() const;
};
