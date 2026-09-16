#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // DCT 係数を残すブロックの一辺の長さを計算
    int keep = MAX(2, (int)round((0.15 + 0.6 * a) * MIN(h, w)));

    // DCT 係数を保持する配列
    double* dct_coeffs = (double*)malloc(h * w * sizeof(double));
    if (dct_coeffs == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // 画像を DCT 変換
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // DCT 変換の実装 (ここでは単純な例として、入力画像の値をそのままコピー)
            dct_coeffs[y * w + x] = in[y * w + x];
        }
    }

    // ローパスフィルタを適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (y < keep && x < keep) {
                // 低周波成分を残す
                out[y * w + x] = dct_coeffs[y * w + x];
            } else {
                // それ以外の成分は 0 に設定
                out[y * w + x] = 0.0;
            }
        }
    }

    // DCT 係数配列を解放
    free(dct_coeffs);
}

// 定数マクロの定義
#define MAX(a, b) ((a) > (b) ? (a) : (b))
#define MIN(a, b) ((a) < (b) ? (a) : (b))
