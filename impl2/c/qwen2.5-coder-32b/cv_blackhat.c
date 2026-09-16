#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 結構要素のサイズを計算 (3 + 2 * int(a * 3)) で、範囲は 3 から 9 まで
    int se_size = 3 + 2 * (int)(a * 3);
    if (se_size < 3) se_size = 3;
    if (se_size > 9) se_size = 9;

    // 結構要素の半径
    int se_radius = se_size / 2;

    // 画像の端を扱う方法: 境界外アクセスを避けるために、入力画像の周囲に余白を追加する
    // ここでは、reflect (d c b a | a b c d) の方法を選択する

    // 余白を追加した画像のサイズ
    int padded_h = h + 2 * se_radius;
    int padded_w = w + 2 * se_radius;

    // 余白を追加した画像を確保
    double* padded_in = (double*)malloc(padded_h * padded_w * sizeof(double));
    if (padded_in == NULL) return;

    // 余白を追加して画像をコピー
    for (int y = 0; y < padded_h; y++) {
        for (int x = 0; x < padded_w; x++) {
            int src_y = y - se_radius;
            int src_x = x - se_radius;

            // 境界外アクセスを reflect する
            if (src_y < 0) src_y = -src_y - 1;
            if (src_y >= h) src_y = 2 * h - src_y - 1;
            if (src_x < 0) src_x = -src_x - 1;
            if (src_x >= w) src_x = 2 * w - src_x - 1;

            padded_in[y * padded_w + x] = in[src_y * w + src_x];
        }
    }

    // 出力画像を初期化
    memset(out, 0, h * w * sizeof(double));

    // 各画素に対して閉処理を行い、元画像から差を計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_value = -INFINITY;

            // 結構要素の範囲内で最大値を求める
            for (int ky = -se_radius; ky <= se_radius; ky++) {
                for (int kx = -se_radius; kx <= se_radius; kx++) {
                    int py = y + se_radius + ky;
                    int px = x + se_radius + kx;
                    if (padded_in[py * padded_w + px] > max_value) {
                        max_value = padded_in[py * padded_w + px];
                    }
                }
            }

            // 閉処理結果から元画像を引く
            out[y * w + x] = max_value - in[y * w + x];
        }
    }

    // 余白を追加した画像を解放
    free(padded_in);
}
