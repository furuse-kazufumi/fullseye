#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 周期的な境界条件を採用
    // 画像の端の値は、反対側の端から周期的に繋がる。

    // フーリエ変換のためのテンポラリ配列
    double* temp = (double*)malloc(h * w * sizeof(double));
    double* fft_in = (double*)malloc(h * w * sizeof(double));
    double* fft_out = (double*)malloc(h * w * sizeof(double));

    // 入力画像を対数変換
    for (int i = 0; i < h * w; i++) {
        temp[i] = log(in[i] + 1e-6); // 0 に近い値を防ぐための小さなオフセット
    }

    // フーリエ変換
    for (int i = 0; i < h * w; i++) {
        fft_in[i] = temp[i];
    }
    // ここにフーリエ変換の実装を追加する（実装は省略）

    // フィルタリング
    for (int i = 0; i < h * w; i++) {
        double freq = sqrt((i % w) * (i % w) + (i / w) * (i / w)) / sqrt(h * w);
        double filter = exp(-a * freq * freq) * (1 + b * freq * freq);
        fft_out[i] = fft_in[i] * filter;
    }

    // 逆フーリエ変換
    // ここに逆フーリエ変換の実装を追加する（実装は省略）

    // 対数を元に戻す
    for (int i = 0; i < h * w; i++) {
        out[i] = exp(fft_out[i]) - 1e-6; // 対数変換時のオフセットを戻す
    }

    // メモリ解放
    free(temp);
    free(fft_in);
    free(fft_out);
}
