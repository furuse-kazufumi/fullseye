#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素のサイズを計算
    int se_size = 3 + 2 * (int)(a * 3);
    if (se_size < 3) se_size = 3; // 最小サイズを保証
    if (se_size > 9) se_size = 9; // 最大サイズを保証

    // 構造要素の半径
    int se_radius = se_size / 2;

    // 出力画像を入力画像と同じに初期化
    memcpy(out, in, h * w * sizeof(double));

    // 画像の各ピクセルに対して処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_val = in[y * w + x]; // 初期値として現在のピクセルの値を設定

            // 構造要素の範囲内のピクセルに対して最大値を更新
            for (int dy = -se_radius; dy <= se_radius; dy++) {
                for (int dx = -se_radius; dx <= se_radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 画像の境界外の場合はスキップ
                    if (ny < 0 || ny >= h || nx < 0 || nx >= w) continue;

                    // 最大値を更新
                    if (in[ny * w + nx] > max_val) {
                        max_val = in[ny * w + nx];
                    }
                }
            }

            // 出力画像に最大値を設定
            out[y * w + x] = max_val;
        }
    }
}
