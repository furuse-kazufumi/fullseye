void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素のサイズを計算
    int kernel_size = (int)(a * 3 + 1); // a が 0.1 から 0.9 の範囲で動くと、kernel_size は 3, 5, 7, 9 に切り替わる
    if (kernel_size % 2 == 0) kernel_size++; // 異なる a の値で kernel_size が奇数になるように調整

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 侵食処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = in[y * w + x];
            int start_y = y - kernel_size / 2;
            int start_x = x - kernel_size / 2;
            for (int ky = 0; ky < kernel_size; ky++) {
                for (int kx = 0; kx < kernel_size; kx++) {
                    int ny = start_y + ky;
                    int nx = start_x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        min_val = fmin(min_val, in[ny * w + nx]);
                    }
                }
            }
            out[y * w + x] = min_val;
        }
    }
}
