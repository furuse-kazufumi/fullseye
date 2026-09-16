void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの計算
    int window_size = 3 + (int)(a * 2); // a は [0, 1] の範囲で、窓サイズは 3/5/7/9 に変化
    int half_window = window_size / 2;

    // 閾値の計算
    double threshold = 0.05 + b * 0.35; // b は [0, 1] の範囲で、閾値は 0.05 から 0.4 に変化

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 画像の各画素に対して処理を適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;

            // 窓内の画素を処理
            for (int dy = -half_window; dy <= half_window; dy++) {
                for (int dx = -half_window; dx <= half_window; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 端の処理: 入力画像の端を折り返す
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;

                    double pixel = in[ny * w + nx];
                    double diff = fabs(pixel - out[y * w + x]);

                    if (diff < threshold) {
                        sum += pixel;
                        count++;
                    }
                }
            }

            // 窓内に閾値未満の画素が存在する場合、平均値を出力
            if (count > 0) {
                out[y * w + x] = sum / count;
            }
        }
    }
}
