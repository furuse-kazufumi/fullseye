#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 伝導度パラメータの計算
    double conductance = 0.5 + 4.5 * a;

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 反復回数の計算
    int iterations = (int)(b * 9);

    // 各ピクセルの近傍を考慮するためのインデックス
    int offsets[9] = { -w - 1, -w, -w + 1, -1, 0, 1, w - 1, w, w + 1 };

    // 曲率異方性拡散の反復処理
    for (int iter = 0; iter < iterations; iter++) {
        for (int y = 1; y < h - 1; y++) {
            for (int x = 1; x < w - 1; x++) {
                double sum = 0.0;
                double div = 0.0;
                for (int k = 0; k < 9; k++) {
                    int ny = y + (offsets[k] / w);
                    int nx = x + (offsets[k] % w);
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double diff = in[y * w + x] - in[ny * w + nx];
                        double weight = exp(-diff * diff / (conductance * conductance));
                        sum += weight * diff;
                        div += weight;
                    }
                }
                out[y * w + x] = in[y * w + x] + 0.0625 * sum / div;
            }
        }

        // 出力画像を入力画像にコピー
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                in[y * w + x] = out[y * w + x];
            }
        }
    }

    // 出力画像のクリッピング
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (out[y * w + x] < 0.0) {
                out[y * w + x] = 0.0;
            } else if (out[y * w + x] > 1.0) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
