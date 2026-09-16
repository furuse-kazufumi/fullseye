void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 二項フィルタのサイズを決定
    int kernel_size = 3 + (int)(a * 3); // a は [0, 1] の範囲で、kernel_size は {3, 5, 7, 9} のいずれか
    if (kernel_size < 3) kernel_size = 3;
    if (kernel_size > 9) kernel_size = 9;

    // 二項係数を計算するための配列
    double binomial_coeffs[kernel_size];
    for (int i = 0; i < kernel_size; ++i) {
        binomial_coeffs[i] = 1.0;
        for (int j = 1; j <= i; ++j) {
            binomial_coeffs[i] *= (i - j + 1) / j;
        }
    }

    // 端の処理: 入力画像の端を重複させて折り返す
    // これは、入力画像の端を拡張するための一時的な配列を用意する
    double extended_in[h + kernel_size - 1][w + kernel_size - 1];
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            extended_in[y + (kernel_size - 1) / 2][x + (kernel_size - 1) / 2] = in[y * w + x];
        }
    }
    // 上下左右に端を折り返す
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < (kernel_size - 1) / 2; ++x) {
            extended_in[y + (kernel_size - 1) / 2][x] = extended_in[y + (kernel_size - 1) / 2][x + 1];
            extended_in[y + (kernel_size - 1) / 2][x + w - 1 + (kernel_size - 1) / 2] = extended_in[y + (kernel_size - 1) / 2][x + w - 2 + (kernel_size - 1) / 2];
        }
        for (int x = 0; x < w; ++x) {
            extended_in[y][x + (kernel_size - 1) / 2] = extended_in[y + 1][x + (kernel_size - 1) / 2];
            extended_in[y + h - 1 + (kernel_size - 1) / 2][x + (kernel_size - 1) / 2] = extended_in[y + h - 2 + (kernel_size - 1) / 2][x + (kernel_size - 1) / 2];
        }
    }

    // 画像の平滑化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            for (int ky = 0; ky < kernel_size; ++ky) {
                for (int kx = 0; kx < kernel_size; ++kx) {
                    sum += extended_in[y + (kernel_size - 1) / 2 + ky][x + (kernel_size - 1) / 2 + kx] * binomial_coeffs[ky] * binomial_coeffs[kx];
                }
            }
            out[y * w + x] = sum / (kernel_size * kernel_size);
        }
    }
}
