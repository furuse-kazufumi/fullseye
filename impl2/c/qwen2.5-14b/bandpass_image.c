#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像のサイズチェック
    if (h <= 0 || w <= 0) {
        return; // 無効なサイズの場合は何もしない
    }

    // フーリエ変換の準備
    double* fft_in = (double*)malloc(h * w * sizeof(double));
    double* fft_out = (double*)malloc(h * w * sizeof(double));
    double* freq_mask = (double*)malloc(h * w * sizeof(double));

    // 入力画像をフーリエ変換
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            fft_in[y * w + x] = in[y * w + x];
        }
    }

    // フーリエ変換
    // ここでは、実装の詳細を省略し、仮想的なフーリエ変換関数 fft_transform を使用する
    fft_transform(fft_in, h, w, fft_out);

    // 周波数領域でのマスク作成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double freq = sqrt((x - w / 2) * (x - w / 2) + (y - h / 2) * (y - h / 2));
            double normalized_freq = freq / sqrt((w / 2) * (w / 2) + (h / 2) * (h / 2));
            freq_mask[y * w + x] = (normalized_freq >= a && normalized_freq <= b) ? 1.0 : 0.0;
        }
    }

    // マスクを適用
    for (int i = 0; i < h * w; i++) {
        fft_out[i] *= freq_mask[i];
    }

    // 逆フーリエ変換
    // ここでは、実装の詳細を省略し、仮想的な逆フーリエ変換関数 ifft_transform を使用する
    ifft_transform(fft_out, h, w, fft_out);

    // 出力画像の生成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = (fft_out[y * w + x] + 1.0) / 2.0; // ゼロ平均の符号つき応答を [0,1] に写像
        }
    }

    // メモリの解放
    free(fft_in);
    free(fft_out);
    free(freq_mask);
}

// 仮想的なフーリエ変換関数
void fft_transform(const double* in, int h, int w, double* out) {
    // 実装は省略
}

// 仮想的な逆フーリエ変換関数
void ifft_transform(const double* in, int h, int w, double* out) {
    // 実装は省略
}
