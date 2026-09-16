void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素のサイズを決定
    int kernel_size = 3 + (int)(a * 4); // a は [0, 1] の範囲で、kernel_size は {3, 5, 7, 9} のいずれか
    if (kernel_size < 3) kernel_size = 3; // 最小値を保証
    if (kernel_size > 9) kernel_size = 9; // 最大値を保証

    // 出力画像を初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // グレースケール収縮処理
    for (int y = kernel_size / 2; y < h - kernel_size / 2; y++) {
        for (int x = kernel_size / 2; x < w - kernel_size / 2; x++) {
            double min_val = in[(y - kernel_size / 2) * w + (x - kernel_size / 2)];
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    double val = in[(y + ky) * w + (x + kx)];
                    if (val < min_val) {
                        min_val = val;
                    }
                }
            }
            out[y * w + x] = min_val;
        }
    }
}
