#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素のサイズを計算
    int se_size = 3 + 2 * (int)(a * 3);
    if (se_size < 3) se_size = 3; // 最小サイズを保証
    if (se_size > 9) se_size = 9; // 最大サイズを保証

    // 開閉処理のためのテンポラリ配列を確保
    double* temp = (double*)malloc(h * w * sizeof(double));
    if (temp == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // 入力画像をコピーしてテンポラリ配列に格納
    for (int i = 0; i < h * w; i++) {
        temp[i] = in[i];
    }

    // 開処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = INFINITY;
            for (int dy = -se_size / 2; dy <= se_size / 2; dy++) {
                for (int dx = -se_size / 2; dx <= se_size / 2; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    // 画像の境界外を無視
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double val = temp[ny * w + nx];
                        if (val < min_val) {
                            min_val = val;
                        }
                    }
                }
            }
            out[y * w + x] = min_val;
        }
    }

    // 画像の最大値を計算
    double max_val = -INFINITY;
    for (int i = 0; i < h * w; i++) {
        if (out[i] > max_val) {
            max_val = out[i];
        }
    }

    // 出力を正規化
    if (max_val > 0) {
        for (int i = 0; i < h * w; i++) {
            out[i] /= max_val;
        }
    }

    // テンポラリ配列を解放
    free(temp);
}
