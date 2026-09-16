void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓の一辺の長さを決定
    int window_size = (int)(4 * a + 0.5); // 0.5 は丸め処理
    window_size = window_size > 0 ? window_size : 3; // 最小値 3
    window_size = window_size % 2 == 0 ? window_size + 1 : window_size; // 奇数に保つ

    // 窓の半径
    int radius = window_size / 2;

    // 出力画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;

            // 窓内の各ピクセルに対して処理を行う
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 端の処理: 端画素を重複させて折り返す
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;

                    sum += in[ny * w + nx];
                    count++;
                }
            }

            // 平均値を計算
            out[y * w + x] = sum / count;
        }
    }
}
