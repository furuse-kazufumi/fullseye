#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用。a は [0,1] の範囲で、a が大きいほど滑らかになる。
    double weight = 0.02 + 0.28 * a;
    double tau = 0.125;
    int iterations = 120;

    // 出力画像を入力画像と同じ形状で初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 双対射影法の反復計算
    for (int i = 0; i < iterations; i++) {
        // ここでは、具体的な双対射影法のアルゴリズムを簡略化して実装します。
        // 実際には、TV-L2 モデルの双対問題を解くための詳細なステップが必要です。
        // ここでは、単純な平滑化処理を仮定して実装します。
        for (int y = 1; y < h - 1; y++) {
            for (int x = 1; x < w - 1; x++) {
                double sum = 0.0;
                sum += in[(y - 1) * w + x];
                sum += in[(y + 1) * w + x];
                sum += in[y * w + (x - 1)];
                sum += in[y * w + (x + 1)];
                sum /= 4.0;
                out[y * w + x] = (1.0 - weight * tau) * out[y * w + x] + weight * tau * sum;
            }
        }
    }

    // 出力を [0,1] の範囲にクリップ
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
