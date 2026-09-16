void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓の一辺 k を決定
    int k = 3 + (int)(a * 3); // a が 0.1 から 0.9 の範囲で動くと、k は 3 から 9 の範囲で動く
    k = k > 1 ? k : 1; // k が 1 未満の場合は 1 にクリップ

    // 窓の半径
    int r = k / 2;

    // 出力画像の各ピクセルに対して平均を計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;

            // 窓内の各ピクセルに対して
            for (int dy = -r; dy <= r; dy++) {
                for (int dx = -r; dx <= r; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 端の処理: 入力画像の端を重複させて折り返す
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;

                    sum += in[ny * w + nx];
                    count++;
                }
            }

            // 平均を計算
            out[y * w + x] = sum / count;
        }
    }
}
