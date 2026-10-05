#include <chrono>
#include <cstdint>
#include <mutex>

extern "C" std::int64_t staticlink_cpp_runtime_probe()
{
    std::mutex mutex;
    std::lock_guard<std::mutex> lock(mutex);
    return std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}
