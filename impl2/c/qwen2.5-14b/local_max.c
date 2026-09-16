void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの計算
    int window_size = (int)(a * (w < h ? w : h)); // 窓サイズは a によって決まる
    window_size = window_size % 2 == 0 ? window_size + 1 : window_size; // 奇数に丸める

    // 出力画像の初期化
    for (int i = 0; i < h * w; ++i) {
        out[i] = 0.0;
    }

    // 局所的な最大値の検出
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double max_val = in[y * w + x]; // まず現在の画素の値を最大値として仮定
            bool is_max = true; // 現在の画素が最大値であるかのフラグ

            // 窓内の画素をチェック
            for (int dy = -window_size / 2; dy <= window_size / 2; ++dy) {
                for (int dx = -window_size / 2; dx <= window_size / 2; ++dx) {
                    int ny = y + dy, nx = x + dx;
                    // 窓内の画素が画像の範囲内にあるかチェック
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (in[ny * w + nx] > max_val) {
                            max_val = in[ny * w + nx];
                            is_max = false; // 最大値が更新された場合、フラグを false に
                        }
                    }
                }
            }

            // 現在の画素が最大値であり、かつしきい値を超える場合、出力画像に 1.0 を設定
            if (is_max && in[y * w + x] > (0.3 + 0.4 * b)) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
