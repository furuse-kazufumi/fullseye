#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の高さと幅を取得
    int height = h;
    int width = w;

    // 出力画像のサイズを確保
    int output_size = height * width;
    double* output = (double*)malloc(output_size * sizeof(double));

    // 画像のエッジ保存平滑化と色の平滑化を適用
    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            // 空間方向の平滑化範囲を計算
            int sigma_s = (int)(20 + (120 - 20) * a);
            // 色差の許容範囲を計算
            double sigma_r = 0.1 + (0.5 - 0.1) * b;

            // 周囲のピクセルを考慮して平滑化処理を適用
            double sum = 0.0;
            int count = 0;
            for (int dy = -sigma_s; dy <= sigma_s; dy++) {
                for (int dx = -sigma_s; dx <= sigma_s; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    // 画像の境界外を処理するための補間
                    if (ny >= 0 && ny < height && nx >= 0 && nx < width) {
                        double pixel = in[ny * width + nx];
                        double distance = sqrt(dy * dy + dx * dx);
                        double weight = exp(-(distance * distance) / (2 * sigma_s * sigma_s));
                        sum += pixel * weight;
                        count += weight;
                    }
                }
            }
            // 平滑化後のピクセル値を計算
            double smoothed_pixel = sum / count;

            // 色差の許容範囲を考慮して最終的なピクセル値を決定
            double input_pixel = in[y * width + x];
            double diff = fabs(smoothed_pixel - input_pixel);
            if (diff <= sigma_r) {
                output[y * width + x] = smoothed_pixel;
            } else {
                output[y * width + x] = input_pixel;
            }
        }
    }

    // 出力画像をコピー
    memcpy(out, output, output_size * sizeof(double));

    // メモリを解放
    free(output);
}
