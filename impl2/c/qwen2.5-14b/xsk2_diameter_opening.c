#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const int DIAMETER_MIN = 4;
    const int DIAMETER_MAX = 34;
    const int DIAMETER_RANGE = DIAMETER_MAX - DIAMETER_MIN + 1;

    // しきい値の計算
    int diameter_threshold = DIAMETER_MIN + (int)(a * DIAMETER_RANGE);

    // マスクの初期化
    int mask_size = diameter_threshold * 2 + 1;
    int* mask = (int*)malloc(mask_size * mask_size * sizeof(int));
    if (mask == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // マスクの作成
    for (int y = -diameter_threshold; y <= diameter_threshold; y++) {
        for (int x = -diameter_threshold; x <= diameter_threshold; x++) {
            mask[(y + diameter_threshold) * mask_size + (x + diameter_threshold)] = (x * x + y * y <= diameter_threshold * diameter_threshold);
        }
    }

    // 出力画像の初期化
    for (int i = 0; i < h * w; i++) {
        out[i] = 0.0;
    }

    // マスクを用いた直径オープニング処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_intensity = 0.0;
            for (int mask_y = -diameter_threshold; mask_y <= diameter_threshold; mask_y++) {
                for (int mask_x = -diameter_threshold; mask_x <= diameter_threshold; mask_x++) {
                    int mask_index = (mask_y + diameter_threshold) * mask_size + (mask_x + diameter_threshold);
                    int image_y = y + mask_y;
                    int image_x = x + mask_x;
                    if (image_y >= 0 && image_y < h && image_x >= 0 && image_x < w) {
                        max_intensity = fmax(max_intensity, in[image_y * w + image_x] * mask[mask_index]);
                    }
                }
            }
            out[y * w + x] = max_intensity;
        }
    }

    // メモリの解放
    free(mask);
}
