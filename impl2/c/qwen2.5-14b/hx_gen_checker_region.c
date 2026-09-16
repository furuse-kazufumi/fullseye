void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // チェッカーボードのセルサイズを計算
    int cell_size = (int)(0.15 * (h < w ? h : w)); // 5% から 25% の範囲
    if (cell_size < 1) {
        cell_size = 1; // 最小セルサイズは 1
    }

    // 出力配列を初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // (row//cell + col//cell) が偶数のセルを前景(1)とする
            if (((y / cell_size) + (x / cell_size)) % 2 == 0) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }
}
