void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。端の処理は反対側へ巻き付ける(周期)とする。

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (y % 2 == 1) { // 偶数行 (0-indexed)
                out[y * w + x] = in[y * w + x];
            } else { // 奇数行 (0-indexed)
                // 上下の行を取得。端は反対側へ巻き付ける。
                int up = (y - 1 + h) % h;
                int down = (y + 1) % h;
                out[y * w + x] = 0.5 * (in[up * w + x] + in[down * w + x]);
            }
        }
    }
}
