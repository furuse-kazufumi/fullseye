#include <fullseye.hpp>

#include <array>
#include <iomanip>
#include <iostream>

int main() {
    try {
        fullseye::Runtime fs;
        const std::array<double, 9> pixels{{0.0, 0.2, 0.0,
                                             0.2, 1.0, 0.2,
                                             0.0, 0.2, 0.0}};
        auto image = fullseye::Image::from_buffer(pixels.data(), 3, 3);
        const auto matches = fs.find("gaussian");
        auto out = fs.call("gaussian", image, {{"a", 0.5}});
        const auto filtered = out.image();
        double sum = 0.0;
        for (int64_t row = 0; row < filtered.height(); ++row)
            for (int64_t column = 0; column < filtered.width(); ++column)
                sum += filtered.at(row, column);
        std::cout << "result_count=" << out.size() << " output_sum="
                  << std::setprecision(17) << sum << '\n';
        return out.size() == 1 && matches.find("registry:gaussian") != std::string::npos ? 0 : 1;
    } catch (const fullseye::Error &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
