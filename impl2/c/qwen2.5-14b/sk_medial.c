#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 二値画像の中心軸変換を実装するための内部関数
    void medial_axis_transform(const double* img, int height, int width, double* result) {
        // 画像の周囲に境界を追加するための拡張画像のサイズ
        int extended_height = height + 2;
        int extended_width = width + 2;
        double* extended_img = (double*)malloc(extended_height * extended_width * sizeof(double));
        double* distance_img = (double*)malloc(height * width * sizeof(double));
        double* result_img = (double*)malloc(height * width * sizeof(double));

        // 入力画像を拡張画像にコピー
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                extended_img[(y + 1) * extended_width + (x + 1)] = img[y * width + x];
            }
        }

        // 拡張画像の境界を0に設定
        for (int x = 0; x < extended_width; x++) {
            extended_img[x] = 0;
            extended_img[(extended_height - 1) * extended_width + x] = 0;
        }
        for (int y = 0; y < extended_height; y++) {
            extended_img[y * extended_width] = 0;
            extended_img[y * extended_width + (extended_width - 1)] = 0;
        }

        // 距離変換を適用
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                int min_distance = 10000; // 大きな初期値
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        if (dy == 0 && dx == 0) continue;
                        int ny = y + dy + 1;
                        int nx = x + dx + 1;
                        int distance = abs(dy) + abs(dx);
                        if (extended_img[ny * extended_width + nx] == 0) {
                            distance = 10000; // 境界からの距離は無限大
                        }
                        if (distance < min_distance) {
                            min_distance = distance;
                        }
                    }
                }
                distance_img[y * width + x] = min_distance;
            }
        }

        // 中心軸変換を適用
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                int is_medial = 1;
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        if (dy == 0 && dx == 0) continue;
                        int ny = y + dy;
                        int nx = x + dx;
                        if (distance_img[y * width + x] <= distance_img[ny * width + nx]) {
                            is_medial = 0;
                            break;
                        }
                    }
                    if (!is_medial) break;
                }
                result_img[y * width + x] = is_medial;
            }
        }

        // 結果を出力画像にコピー
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                result[y * width + x] = result_img[y * width + x];
            }
        }

        // メモリを解放
        free(extended_img);
        free(distance_img);
        free(result_img);
    }

    // 入力画像を二値化
    for (int i = 0; i < h * w; i++) {
        out[i] = (in[i] > 0.5) ? 1.0 : 0.0;
    }

    // 中心軸変換を適用
    medial_axis_transform(out, h, w, out);

    // メモリを解放
    // ここではメモリを解放する必要がないため、コメントアウト
    // free(out);
}
