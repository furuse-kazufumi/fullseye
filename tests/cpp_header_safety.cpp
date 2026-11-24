// C++ header ownership and span-boundary gate / C++ header の所有権・span 境界の門。
#include <fullseye.hpp>

#include <cstddef>
#include <span>
#include <stdexcept>
#include <type_traits>

#ifdef _WIN32
#  define WIN32_LEAN_AND_MEAN
#  include <windows.h>
#else
#  include <sys/mman.h>
#  include <unistd.h>
#endif

namespace {

class GuardedDouble {
public:
    GuardedDouble() {
#ifdef _WIN32
        SYSTEM_INFO info;
        GetSystemInfo(&info);
        page_size_ = static_cast<size_t>(info.dwPageSize);
        allocation_ = VirtualAlloc(nullptr, 2u * page_size_, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
        if (allocation_ == nullptr) throw std::runtime_error("VirtualAlloc failed");
        DWORD old_protection = 0u;
        if (VirtualProtect(static_cast<unsigned char *>(allocation_) + page_size_, page_size_,
                           PAGE_NOACCESS, &old_protection) == 0) {
            VirtualFree(allocation_, 0u, MEM_RELEASE);
            throw std::runtime_error("VirtualProtect failed");
        }
#else
        const long system_page_size = sysconf(_SC_PAGESIZE);
        if (system_page_size <= 0) throw std::runtime_error("sysconf(_SC_PAGESIZE) failed");
        page_size_ = static_cast<size_t>(system_page_size);
        allocation_ = mmap(nullptr, 2u * page_size_, PROT_READ | PROT_WRITE,
                           MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (allocation_ == MAP_FAILED) {
            allocation_ = nullptr;
            throw std::runtime_error("mmap failed");
        }
        if (mprotect(static_cast<unsigned char *>(allocation_) + page_size_, page_size_, PROT_NONE) != 0) {
            munmap(allocation_, 2u * page_size_);
            allocation_ = nullptr;
            throw std::runtime_error("mprotect failed");
        }
#endif
        data_ = reinterpret_cast<double *>(static_cast<unsigned char *>(allocation_) + page_size_ - sizeof(double));
        *data_ = 1.0;
    }

    ~GuardedDouble() {
#ifdef _WIN32
        if (allocation_ != nullptr) VirtualFree(allocation_, 0u, MEM_RELEASE);
#else
        if (allocation_ != nullptr) munmap(allocation_, 2u * page_size_);
#endif
    }

    GuardedDouble(const GuardedDouble &) = delete;
    GuardedDouble &operator=(const GuardedDouble &) = delete;
    const double *data() const noexcept { return data_; }

private:
    void *allocation_ = nullptr;
    size_t page_size_ = 0u;
    double *data_ = nullptr;
};

}  // namespace

int main() {
    static_assert(!std::is_constructible_v<fullseye::Result, fs_result_id_t>,
                  "Only Runtime may adopt a result ID");
    const std::string diagnosis = fullseye::Runtime::diagnose();
    if (diagnosis.find("Tried:") == std::string::npos
        || diagnosis.find("FULLSEYE_PYTHON_ROOT") == std::string::npos) return 2;

    GuardedDouble guarded;
    try {
        // The next double is in a no-access page. A copy before checking the
        // span length would fault; the API must instead throw invalid_argument.
        // 次の double はアクセス不可 page にある。copy 前に span 長を検査する。
        (void)fullseye::Image::from_buffer(std::span<const double>(guarded.data(), 1u), 1, 2,
                                            fullseye::BufferOwnership::copy);
        return 1;
    } catch (const std::invalid_argument &) {
        return 0;
    }
}
