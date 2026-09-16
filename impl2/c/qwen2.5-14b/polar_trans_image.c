#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の中心座標
    int center_x = w / 2;
    int center_y = h / 2;
    // 最大半径
    int max_radius = (h < w) ? h / 2 : w / 2;

    // 出力画像の幅と高さ
    int out_w = max_radius * 2;
    int out_h = max_radius;

    // 出力画像の初期化
    for (int y = 0; y < out_h; y++) {
        for (int x = 0; x < out_w; x++) {
            out[y * out_w + x] = 0.0;
        }
    }

    // 极座標変換
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // ピクセルの直交座標
            int dx = x - center_x;
            int dy = y - center_y;
            // ピクセルの極座標
            double radius = sqrt(dx * dx + dy * dy);
            double angle = atan2(dy, dx);
            // 極座標から直交座標への変換
            int out_x = center_x + radius * cos(angle);
            int out_y = center_y + radius * sin(angle);

            // 画像の範囲内に収まるかチェック
            if (out_x >= 0 && out_x < w && out_y >= 0 && out_y < h) {
                // 出力画像の座標
                int out_idx = (int)(angle / (2 * M_PI) * out_w);
                int out_y_idx = (int)radius;
                // 出力画像のインデックス
                int out_idx_final = out_y_idx * out_w + out_idx;
                // ピクセル値のコピー
                out[out_idx_final] = in[y * w + x];
            }
        }
    }
}
