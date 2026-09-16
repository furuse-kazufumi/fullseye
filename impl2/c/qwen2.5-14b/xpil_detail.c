#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端を処理する際、境界外のピクセルは近傍のピクセルを使用する。
    // これは、画像の端をどのように処理するかの選択であり、仕様書では明示的に定義されていない。

    // ディテール強調フィルタのカーネル
    const double kernel[9] = {
        -1, -1, -1,
        -1,  8, -1,
        -1, -1, -1
    };

    // 出力画像の各ピクセルを計算
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double sum = 0.0;
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int iy = y + ky;
                    int ix = x + kx;
                    if (iy < 0 || iy >= h || ix < 0 || ix >= w) {
                        // 端のピクセルは近傍のピクセルを使用
                        iy = (iy < 0) ? 0 : (iy >= h ? h - 1 : iy);
                        ix = (ix < 0) ? 0 : (ix >= w ? w - 1 : ix);
                    }
                    sum += in[iy * w + ix] * kernel[(ky + 1) * 3 + (kx + 1)];
                }
            }
            out[y * w + x] = fmax(0.0, fmin(1.0, sum)); // 出力の値域を [0, 1] に制限
        }
    }

    // 画像の端のピクセルは元の値をそのまま出力
    for (int y = 0; y < h; y++) {
        out[y * w] = in[y * w];
        out[y * w + w - 1] = in[y * w + w - 1];
    }
    for (int x = 0; x < w; x++) {
        out[x] = in[x];
        out[(h - 1) * w + x] = in[(h - 1) * w + x];
    }
}
