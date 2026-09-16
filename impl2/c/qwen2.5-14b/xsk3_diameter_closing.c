#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const int DIAMETER_THRESHOLD_MIN = 4;
    const int DIAMETER_THRESHOLD_MAX = 34;
    const int DIAMETER_THRESHOLD_RANGE = DIAMETER_THRESHOLD_MAX - DIAMETER_THRESHOLD_MIN + 1;

    // パラメータ a を使用して直径の閾値を計算
    int diameter_threshold = DIAMETER_THRESHOLD_MIN + (int)(a * DIAMETER_THRESHOLD_RANGE);

    // 出力画像を入力画像と同じにする初期化
    memcpy(out, in, h * w * sizeof(double));

    // 画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 8近傍のマスク
            int mask[9] = {0};
            int mask_index = 0;

            // 8近傍のピクセルを取得
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    // 画像の範囲外の場合は無視
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        mask[mask_index++] = (int)(in[ny * w + nx] > 0.5);
                    }
                }
            }

            // 8近傍のマスクから外接矩形の対角線長を計算
            int rect_width = 0;
            int rect_height = 0;
            for (int i = 0; i < 9; i++) {
                if (mask[i] == 1) {
                    rect_width = fmax(rect_width, i % 3);
                    rect_height = fmax(rect_height, i / 3);
                }
            }
            int diameter = (int)sqrt(rect_width * rect_width + rect_height * rect_height);

            // 直径が閾値より大きい場合はピクセルを保持
            if (diameter >= diameter_threshold) {
                out[y * w + x] = in[y * w + x];
            } else {
                out[y * w + x] = 0.0; // 閾値未満の場合は背景値(0.0)に設定
            }
        }
    }
}
