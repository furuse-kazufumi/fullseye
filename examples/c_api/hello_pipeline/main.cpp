#include <fullseye.hpp>

#include <array>
#include <iostream>

int main() {
    try {
        const std::array<double, 9> pixels{{0.0, 0.2, 0.0,
                                             0.2, 1.0, 0.2,
                                             0.0, 0.2, 0.0}};
        auto image = fullseye::Image::from_buffer(pixels.data(), 3, 3);

        // inspect.json is the UTF-8 file Studio writes with Save pipeline.
        // No pipeline code is compiled into this executable: replace the JSON,
        // load it again, and the same app executes the revised pipeline.  The
        // C++ Runtime owner deliberately leaves scope before run(): Pipeline
        // keeps the native runtime alive until the pipeline is destroyed.
        auto pipeline = [] {
            fullseye::Runtime fs;
            return fs.load_pipeline("inspect.json");
        }();
        const auto input = pipeline.input();
        const auto output = pipeline.output();
        auto out = pipeline.run({{"image", image}});

        std::cout << "input=" << input.name << " input_kind=" << input.kind
                  << " output=" << output.name << " output_kind=" << output.kind
                  << " result_count=" << out.size() << " run_count=" << out.region_runs().size() << '\n';
        return input.name == "image" && input.kind == FS_VALUE_IMAGE
               && output.name == "result" && output.kind == FS_VALUE_REGION
               && out.size() == 1u ? 0 : 1;
    } catch (const fullseye::Error &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
