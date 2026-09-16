void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの決定
    int window_size = 3 + (int)(a * 3); // a が 0.1 から 0.9 まで変化するとき、window_size は 3 から 9 まで変化する。
    if (window_size % 2 == 0) {
        window_size++; // 窓サイズは奇数でなければならない
    }

    // 辺のパディングサイズ
    int padding = window_size / 2;

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 画像の各ピクセルに対して処理を実行
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 窓内のピクセルの値を格納する配列
            double window[window_size * window_size];
            int window_index = 0;

            // 窓内のピクセルを取得
            for (int dy = -padding; dy <= padding; dy++) {
                for (int dx = -padding; dx <= padding; dx++) {
                    int py = y + dy;
                    int px = x + dx;

                    // 端の処理: 入力画像の端を折り返す
                    if (py < 0) py = -py - 1;
                    if (py >= h) py = 2 * h - py - 1;
                    if (px < 0) px = -px - 1;
                    if (px >= w) px = 2 * w - px - 1;

                    window[window_index++] = in[py * w + px];
                }
            }

            // 窓内の値をソート
            for (int i = 0; i < window_size * window_size - 1; i++) {
                for (int j = 0; j < window_size * window_size - i - 1; j++) {
                    if (window[j] > window[j + 1]) {
                        double temp = window[j];
                        window[j] = window[j + 1];
                        window[j + 1] = temp;
                    }
                }
            }

            // 20% と 80% のパーセンタイルの平均を計算
            int start_index = window_size * window_size * 0.2;
            int end_index = window_size * window_size * 0.8;
            double trimmed_mean = 0.0;
            for (int i = start_index; i < end_index; i++) {
                trimmed_mean += window[i];
            }
            trimmed_mean /= (end_index - start_index);

            // 出力画像に結果を設定
            out[y * w + x] = trimmed_mean;
        }
    }
}
