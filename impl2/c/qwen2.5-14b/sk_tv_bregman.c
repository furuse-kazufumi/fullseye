#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 平滑化の強さを制御するためのパラメータ
    double weight = 1.0 + 8.0 * a;

    // 画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // ピクセルのインデックス
            int idx = y * w + x;

            // 周囲のピクセルのインデックス
            int idx_up = (y > 0) ? (y - 1) * w + x : idx; // 上のピクセル
            int idx_down = (y < h - 1) ? (y + 1) * w + x : idx; // 下のピクセル
            int idx_left = (x > 0) ? y * w + x - 1 : idx; // 左のピクセル
            int idx_right = (x < w - 1) ? y * w + x + 1 : idx; // 右のピクセル

            // 周囲のピクセルとの差分を計算
            double diff_up = in[idx_up] - in[idx];
            double diff_down = in[idx_down] - in[idx];
            double diff_left = in[idx_left] - in[idx];
            double diff_right = in[idx_right] - in[idx];

            // 全変動正則化の計算
            double tv = sqrt(diff_up * diff_up + diff_down * diff_down + diff_left * diff_left + diff_right * diff_right);

            // 平滑化後のピクセル値を計算
            double smooth_value = in[idx] + weight * (diff_up + diff_down + diff_left + diff_right) / (4.0 * tv + 1e-6);

            // 出力画像に書き込む
            out[idx] = smooth_value;
        }
    }
}
