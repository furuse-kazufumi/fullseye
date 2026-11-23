// Fullseye C++17 RAII example / Fullseye C++17 RAII の例。
#include "fullseye.hpp"

#include <array>
#include <iostream>

int main(int argc, char **argv) {
    try {
        fs_init_options_t options = FS_INIT_OPTIONS_INIT;
        if (argc > 1) {
            options.runtime_root = argv[1];
        }
        fullseye::Runtime runtime(options);
        std::array<double, 6> pixels{{0.0, 0.7, 0.8, 0.2, 0.9, 0.0}};
        fs_input_t input = FS_INPUT_INIT;
        input.image.data = pixels.data();
        input.image.data_bytes = pixels.size() * sizeof(double);
        input.image.width = 3;
        input.image.height = 2;
        input.image.row_stride_bytes = 3 * static_cast<int64_t>(sizeof(double));
        auto result = runtime.call("contract:threshold", {input}, "{\"lo\":0.6,\"hi\":1.0}");
        if (result.size() != 1 || runtime.find_ops().find("registry:blob_count") == std::string::npos) {
            return 1;
        }
        return 0;
    } catch (const fullseye::Error &error) {
        std::cerr << "Fullseye error " << error.status() << ": " << error.what() << '\n';
        return 1;
    }
}
