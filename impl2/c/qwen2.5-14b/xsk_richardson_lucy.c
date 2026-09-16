#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // PSF (Point Spread Function) の定義
    const int psf_size = 3;
    const double psf[psf_size * psf_size] = {
        1.0 / 9.0, 1.0 / 9.0, 1.0 / 9.0,
        1.0 / 9.0, 1.0 / 9.0, 1.0 / 9.0,
        1.0 / 9.0, 1.0 / 9.0, 1.0 / 9.0
    };

    // 反復回数の計算
    int iterations = (int)(a * 16 + 2); // a は [0, 1] の範囲で、反復回数は 2 から 17 まで

    // 出力画像の初期化
    for (int i = 0; i < h * w; ++i) {
        out[i] = in[i];
    }

    // Richardson-Lucy デコンボリューションの反復処理
    for (int iter = 0; iter < iterations; ++iter) {
        // 画像のコピー
        double temp[h * w];
        for (int i = 0; i < h * w; ++i) {
            temp[i] = out[i];
        }

        // デコンボリューション
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                double sum = 0.0;
                for (int py = -1; py <= 1; ++py) {
                    for (int px = -1; px <= 1; ++px) {
                        int ty = y + py;
                        int tx = x + px;
                        if (ty >= 0 && ty < h && tx >= 0 && tx < w) {
                            sum += psf[(py + 1) * psf_size + (px + 1)] * temp[ty * w + tx];
                        }
                    }
                }
                out[y * w + x] *= sum;
            }
        }

        // 画像のコピー
        for (int i = 0; i < h * w; ++i) {
            temp[i] = out[i];
        }

        // デコンボリューションの逆操作
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                double sum = 0.0;
                for (int py = -1; py <= 1; ++py) {
                    for (int px = -1; px <= 1; ++px) {
                        int ty = y + py;
                        int tx = x + px;
                        if (ty >= 0 && ty < h && tx >= 0 && tx < w) {
                            sum += psf[(py + 1) * psf_size + (px + 1)] * temp[ty * w + tx];
                        }
                    }
                }
                out[y * w + x] *= sum;
            }
        }
    }
}
