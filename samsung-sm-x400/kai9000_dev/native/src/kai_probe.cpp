#include <iostream>

int main() {
#if defined(__aarch64__)
    constexpr const char* arch = "aarch64";
#elif defined(__x86_64__)
    constexpr const char* arch = "x86_64";
#else
    constexpr const char* arch = "other";
#endif

    std::cout << "KAI9000_NATIVE_FORGE_GREEN\n";
    std::cout << "arch=" << arch << "\n";
    std::cout << "cxx=" << __cplusplus << "\n";
    return 0;
}
