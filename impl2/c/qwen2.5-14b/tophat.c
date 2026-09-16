void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素の一辺の長さを計算
    int kernel_size = (int)(a * 9) + 3; // a は [0, 1] の範囲で、kernel_size は 3, 5, 7, 9 のいずれか
    if (kernel_size % 2 == 0) {
        kernel_size++; // 奇数に丸める
    }

    // オープニング処理
    double* opening = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_val = in[y * w + x];
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        max_val = fmax(max_val, in[ny * w + nx]);
                    }
                }
            }
            opening[y * w + x] = max_val;
        }
    }

    // ホワイトトップハット変換
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x] - opening[y * w + x];
        }
    }

    // メモリ解放
    free(opening);
}
