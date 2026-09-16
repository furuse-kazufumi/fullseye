#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 端の処理のために、入力画像の境界を拡張する
    // 画像の境界を重複させて折り返す
    // これは、入力画像の境界を拡張した仮想的な画像を想定し、その境界を用いて計算を行う
    // 仮想的な画像の高さと幅は、元の高さと幅に2を加えたもの
    int vh = h + 2;
    int vw = w + 2;
    double* v_in = (double*)malloc(vh * vw * sizeof(double));

    // 仮想的な画像の境界を元の画像の端で折り返す
    for (int y = 0; y < vh; y++) {
        for (int x = 0; x < vw; x++) {
            int oy = y - 1;
            int ox = x - 1;
            if (oy < 0) oy = 0;
            if (ox < 0) ox = 0;
            if (oy >= h) oy = h - 1;
            if (ox >= w) ox = w - 1;
            v_in[y * vw + x] = in[oy * w + ox];
        }
    }

    // unsharp フィルタを適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double blur = 0.0;
            // 3x3 のマスクを使用してぼかしを計算
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int vy = y + ky + 1;
                    int vx = x + kx + 1;
                    blur += v_in[vy * vw + vx];
                }
            }
            blur /= 9.0; // 3x3 マスクの平均値を計算

            // unsharp フィルタの適用
            double v = in[y * w + x];
            out[y * w + x] = v + a * (v - blur);
        }
    }

    // メモリを解放
    free(v_in);
}
