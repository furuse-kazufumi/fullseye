#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 結構要素のサイズを計算 (3 + 2 * int(a * 3)) で、最小3、最大9に制限
    int se_size = 3 + 2 * (int)(a * 3);
    if (se_size < 3) se_size = 3;
    if (se_size > 9) se_size = 9;

    // 結構要素の半径
    int se_radius = se_size / 2;

    // 画像の端を処理する方法: 境界外のピクセルは無視する (zero-padding相当)
    // これは仕様書で明示されていないため、ここではこの方法を選択する

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = 1.0; // 最小値を1.0 (最大値)で初期化

            // 結構要素の範囲内を走査
            for (int ky = -se_radius; ky <= se_radius; ky++) {
                for (int kx = -se_radius; kx <= se_radius; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // 境界内かチェック
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (in[ny * w + nx] < min_val) {
                            min_val = in[ny * w + nx];
                        }
                    }
                }
            }

            // 出力に最小値を設定
            out[y * w + x] = min_val;
        }
    }
}
