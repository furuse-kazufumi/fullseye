void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの計算
    int window_size = (int)(a * (h + w - 2) + 1);
    int half_window = window_size / 2;

    // 辺の処理: 端画素を重複させて折り返す
    // これは、入力画像の境界を拡張するための仮想的な画像を作成します。
    // 画像の各辺を window_size - 1 個のピクセルで拡張します。
    int extended_h = h + 2 * (window_size - 1);
    int extended_w = w + 2 * (window_size - 1);
    double* extended_in = (double*)malloc(extended_h * extended_w * sizeof(double));

    // 元の画像を拡張画像の中央に配置
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            extended_in[(y + window_size - 1) * extended_w + (x + window_size - 1)] = in[y * w + x];
        }
    }

    // 画像の各辺を折り返して拡張
    for (int y = 0; y < window_size - 1; y++) {
        for (int x = 0; x < extended_w; x++) {
            extended_in[y * extended_w + x] = extended_in[(2 * (window_size - 1) - y) * extended_w + x];
            extended_in[(extended_h - 1 - y) * extended_w + x] = extended_in[(y + (window_size - 1)) * extended_w + x];
        }
    }
    for (int x = 0; x < window_size - 1; x++) {
        for (int y = 0; y < extended_h; y++) {
            extended_in[y * extended_w + x] = extended_in[y * extended_w + (2 * (window_size - 1) - x)];
            extended_in[y * extended_w + (extended_w - 1 - x)] = extended_in[y * extended_w + (x + (window_size - 1))];
        }
    }

    // 出力画像の生成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 窓内のピクセルを取得
            double window[window_size * window_size];
            int window_index = 0;
            for (int dy = -half_window; dy <= half_window; dy++) {
                for (int dx = -half_window; dx <= half_window; dx++) {
                    window[window_index++] = extended_in[(y + dy + window_size - 1) * extended_w + (x + dx + window_size - 1)];
                }
            }

            // 窓内のピクセルをソート
            qsort(window, window_size * window_size, sizeof(double), compare);

            // パーセンタイルの計算
            int percentile_index = (int)((b - 0.5) * (window_size * window_size - 1) + 0.5);
            out[y * w + x] = window[percentile_index];
        }
    }

    // 拡張画像のメモリを解放
    free(extended_in);
}

// 比較関数
int compare(const void* a, const void* b) {
    return (*(double*)a - *(double*)b);
}
