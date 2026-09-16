#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 辺のパディングを考慮するための内部画像サイズ
    int h_pad = h + 2;
    int w_pad = w + 2;
    
    // パディングされた画像領域
    double in_pad[h_pad * w_pad];
    
    // 入力画像をパディングされた領域にコピー
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            in_pad[(y + 1) * w_pad + (x + 1)] = in[y * w + x];
        }
    }
    
    // パディングの境界をコピー
    for (int x = 0; x < w_pad; x++) {
        in_pad[x] = in_pad[w_pad]; // 上端
        in_pad[(h_pad - 1) * w_pad + x] = in_pad[(h_pad - 2) * w_pad]; // 下端
    }
    for (int y = 0; y < h_pad; y++) {
        in_pad[y * w_pad] = in_pad[y * w_pad + 1]; // 左端
        in_pad[y * w_pad + w_pad - 1] = in_pad[y * w_pad + w_pad - 2]; // 右端
    }
    
    // TV denoising 本体
    double weight = 0.02 + 0.3 * a;
    double epsilon = 2.0 * weight;
    double delta = 0.25;
    double theta = 0.5;
    
    for (int iter = 0; iter < 500; iter++) {
        for (int y = 1; y < h_pad - 1; y++) {
            for (int x = 1; x < w_pad - 1; x++) {
                double dx = in_pad[y * w_pad + x + 1] - in_pad[y * w_pad + x - 1];
                double dy = in_pad[(y + 1) * w_pad + x] - in_pad[(y - 1) * w_pad + x];
                double norm = sqrt(dx * dx + dy * dy);
                if (norm > epsilon) {
                    dx /= norm;
                    dy /= norm;
                } else {
                    dx = 0.0;
                    dy = 0.0;
                }
                in_pad[y * w_pad + x] += theta * (dx + dy);
            }
        }
        theta *= delta;
        if (theta < 1e-4) break;
    }
    
    // パディングを除去して出力画像にコピー
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in_pad[(y + 1) * w_pad + (x + 1)];
        }
    }
}
