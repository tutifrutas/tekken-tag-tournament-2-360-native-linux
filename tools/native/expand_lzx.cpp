// Expand an Xbox 360 LZX container (magic 0FF512ED/EE) to the plain archive the game
// addresses. Ported from port/src/setup/game_data.cpp ExpandContainer (upstream installer).
// Usage: ttt2_expand_lzx <container> <output> [expected-size]
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

extern "C" {
#include <mspack.h>
#include <lzx.h>
}

namespace {

uint32_t Be32(const uint8_t* p) { return uint32_t(p[0]) << 24 | uint32_t(p[1]) << 16 | uint32_t(p[2]) << 8 | p[3]; }
uint16_t Be16(const uint8_t* p) { return uint16_t(p[0] << 8 | p[1]); }

struct ReadStream { const uint8_t* data; const uint8_t* end; int size; int pad; };
struct WriteStream { uint8_t* data; size_t size; };

int MspackRead(mspack_file* file, void* buffer, int bytes) {
  auto* s = reinterpret_cast<ReadStream*>(file);
  if (s->size == 0) {
    // Frames start on even bytes: an odd frame owes one synthesised pad byte.
    if (s->pad) {
      s->pad = 0;
      if (bytes < 1) return 0;
      *static_cast<uint8_t*>(buffer) = 0;
      return 1;
    }
    if (s->data + 2 > s->end) return 0;
    uint16_t size = Be16(s->data);
    s->data += 2;
    if ((size & 0xFF00) == 0xFF00) {
      if (s->data + 3 > s->end) return 0;
      s->data += 1;
      size = Be16(s->data);
      s->data += 2;
    }
    s->size = size;
    s->pad = size & 1;
  }
  const int n = int(std::min<ptrdiff_t>(std::min(s->size, bytes), s->end - s->data));
  if (n <= 0) return 0;
  std::memcpy(buffer, s->data, n);
  s->data += n;
  s->size -= n;
  return n;
}
int MspackWrite(mspack_file* file, void* buffer, int bytes) {
  auto* s = reinterpret_cast<WriteStream*>(file);
  const size_t n = std::min(s->size, size_t(bytes));
  std::memcpy(s->data, buffer, n);
  s->data += n;
  s->size -= n;
  return int(n);
}
void* MspackAlloc(mspack_system*, size_t n) { return operator new(n); }
void MspackFree(void* p) { operator delete(p); }
void MspackCopy(void* src, void* dst, size_t n) { std::memcpy(dst, src, n); }
mspack_system g_sys = {nullptr, nullptr, MspackRead, MspackWrite, nullptr, nullptr, nullptr,
                       MspackAlloc, MspackFree, MspackCopy};

size_t DecodeChunk(const uint8_t* src, size_t src_len, uint8_t* dst, size_t dst_len) {
  ReadStream rs{src, src + src_len, 0, 0};
  WriteStream ws{dst, dst_len};
  lzxd_stream* lzx = lzxd_init(&g_sys, reinterpret_cast<mspack_file*>(&rs),
                               reinterpret_cast<mspack_file*>(&ws), 17, 0,
                               int(std::min<size_t>(src_len, 0x10000)), off_t(dst_len), 0);
  if (!lzx) return 0;
  lzxd_decompress(lzx, off_t(dst_len));
  lzxd_free(lzx);
  return dst_len - ws.size;
}

constexpr uint32_t kChunkAlign = 0x20000;

int Fail(const char* why) {
  std::fprintf(stderr, "ttt2_expand_lzx: %s\n", why);
  return 1;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc != 3 && argc != 4) return Fail("usage: ttt2_expand_lzx <container> <output> [expected-size]");
  std::ifstream in_file(argv[1], std::ios::binary);
  std::vector<uint8_t> source((std::istreambuf_iterator<char>(in_file)), {});
  if (source.size() < 16) return Fail("container is truncated");
  const uint32_t magic = Be32(source.data());
  if (magic != 0x0FF512EDu && magic != 0x0FF512EEu) return Fail("not an LZX container");

  // Header: magic, version, hash, flags (bit 22: u32 sizes, else packed 20-bit sizes), then
  // one uncompressed size per 0x20000-aligned chunk of the container.
  const size_t source_size = source.size();
  const uint32_t chunks = uint32_t((source_size + kChunkAlign - 1) / kChunkAlign);
  const size_t first = std::min<size_t>(source_size, kChunkAlign);
  const uint32_t flags = Be32(source.data() + 12);
  std::vector<uint32_t> table(chunks);
  size_t header_end;
  if (flags & (1u << 22)) {
    header_end = 16 + 4 * size_t(chunks);
    if (header_end >= first) return Fail("invalid header");
    for (uint32_t i = 0; i < chunks; ++i) table[i] = Be32(source.data() + 16 + 4 * i);
  } else {
    header_end = (16 + (20 * size_t(chunks) + 7) / 8 + 3) & ~size_t(3);
    if (header_end >= first) return Fail("invalid header");
    for (uint32_t i = 0; i < chunks; ++i) {
      const size_t bit = size_t(i) * 20;
      const uint8_t* p = source.data() + 16 + bit / 8;
      const uint32_t w = uint32_t(p[0]) << 16 | uint32_t(p[1]) << 8 | p[2];
      table[i] = (w >> (4 - bit % 8)) & 0xFFFFFu;
    }
  }
  uint64_t total = 0;
  for (uint32_t v : table) total += v;
  if (argc == 4 && total != std::stoull(argv[3])) return Fail("size table does not match the expected size");

  std::ofstream out(argv[2], std::ios::binary | std::ios::trunc);
  if (!out) return Fail("cannot write output");
  std::vector<uint8_t> chunk;
  for (uint32_t k = 0; k < chunks; ++k) {
    const size_t begin = std::max<size_t>(header_end, size_t(k) * kChunkAlign);
    const size_t end = std::min<size_t>(size_t(k + 1) * kChunkAlign, source_size);
    if (begin >= end) return Fail("chunk out of range");
    const uint8_t* in = source.data() + begin;
    const size_t length = end - begin;
    chunk.assign(table[k], 0);
    size_t got;
    if (table[k] + 2 == length && Be16(in) == 0) {  // stored chunk
      std::memcpy(chunk.data(), in + 2, table[k]);
      got = table[k];
    } else {
      got = DecodeChunk(in, length, chunk.data(), table[k]);
    }
    if (got != table[k]) return Fail("chunk failed to decompress");
    if (k == 0 && (chunk.size() < 12 || std::memcmp(chunk.data() + 4, "ftypnrfi", 8) != 0))
      return Fail("decompressed to unexpected data");
    out.write(reinterpret_cast<const char*>(chunk.data()), std::streamsize(chunk.size()));
  }
  out.close();
  if (!out) return Fail("write failed");
  std::printf("expanded %llu bytes\n", static_cast<unsigned long long>(total));
  return 0;
}
