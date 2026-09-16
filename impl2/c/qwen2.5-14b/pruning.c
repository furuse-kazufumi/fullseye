#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端を背景(0)とみなす。
    // 画像の外側は背景(0)とみなす。境界画素の近傍は内部画素のみを考慮する。

    // 出力画像を初期化
    memset(out, 0, h * w * sizeof(double));

    // 端点画素の削除回数を計算
    int prune_count = (int)(1 + 4 * a); // 1〜5 回の範囲で削除

    // 画像の各画素に対して処理を行う
    for (int i = 0; i < prune_count; i++) {
        // 一時的な出力バッファを確保
        double* temp_out = (double*)malloc(h * w * sizeof(double));
        memset(temp_out, 0, h * w * sizeof(double));

        // 画像の各画素に対して処理を行う
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                // 画素が領域に属するかチェック
                if (in[y * w + x] == 1.0) {
                    // 画素の近傍をチェック
                    int neighbors = 0;
                    for (int dy = -1; dy <= 1; dy++) {
                        for (int dx = -1; dx <= 1; dx++) {
                            if (dy == 0 && dx == 0) continue; // 自身を除く
                            int ny = y + dy;
                            int nx = x + dx;
                            // 画像の外側は背景(0)とみなす
                            if (ny < 0 || ny >= h || nx < 0 || nx >= w) continue;
                            if (in[ny * w + nx] == 1.0) neighbors++;
                        }
                    }
                    // 近傍数が 1 以下の端点画素を削除
                    if (neighbors <= 1) {
                        temp_out[y * w + x] = 0.0;
                    } else {
                        temp_out[y * w + x] = 1.0;
                    }
                }
            }
        }

        // 一時的な出力バッファを正式な出力バッファにコピー
        memcpy(out, temp_out, h * w * sizeof(double));

        // 一時的な出力バッファを解放
        free(temp_out);
    }
}
