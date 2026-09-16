#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const int patch_size = 5; // パッチサイズは固定
    const double h_base = 0.02; // 基準カットオフ距離
    const double h_range = 0.20; // カットオフ距離の範囲
    const double h = h_base + h_range * a; // 実際のカットオフ距離

    // 出力画像の初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 非局所平均法の適用
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            double weight_sum = 0.0;

            // パッチの中心を固定
            for (int py = -patch_size / 2; py <= patch_size / 2; ++py) {
                for (int px = -patch_size / 2; px <= patch_size / 2; ++px) {
                    int py_abs = y + py;
                    int px_abs = x + px;

                    // 画像の境界外を無視
                    if (py_abs < 0 || py_abs >= h || px_abs < 0 || px_abs >= w) continue;

                    // パッチ間の距離の計算
                    double patch_distance = 0.0;
                    for (int py_patch = -patch_size / 2; py_patch <= patch_size / 2; ++py_patch) {
                        for (int px_patch = -patch_size / 2; px_patch <= patch_size / 2; ++px_patch) {
                            int py_patch_abs = py_abs + py_patch;
                            int px_patch_abs = px_abs + px_patch;

                            // 画像の境界外を無視
                            if (py_patch_abs < 0 || py_patch_abs >= h || px_patch_abs < 0 || px_patch_abs >= w) continue;

                            // パッチ間の距離の計算
                            double pixel_diff = in[(py_patch_abs * w + px_patch_abs)] - in[(y * w + x)];
                            patch_distance += pixel_diff * pixel_diff;
                        }
                    }

                    // 重みの計算
                    double weight = exp(-patch_distance / (2.0 * h * h));
                    sum += weight * in[(py_abs * w + px_abs)];
                    weight_sum += weight;
                }
            }

            // 重み付き平均の計算
            if (weight_sum > 0.0) {
                out[y * w + x] = sum / weight_sum;
            }
        }
    }
}
