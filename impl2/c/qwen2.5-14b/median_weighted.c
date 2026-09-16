void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの決定
    int window_size = 3; // デフォルト値
    if (a < 0.25) {
        window_size = 3;
    } else if (a < 0.49) {
        window_size = 5;
    } else if (a < 0.75) {
        window_size = 7;
    } else {
        window_size = 9;
    }

    // 窓サイズが奇数であることを確認
    if (window_size % 2 == 0) {
        window_size++;
    }

    // 窓の半径
    int radius = window_size / 2;

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 中央値フィルタの適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 窓内の画素値を格納する配列
            double window[window_size * window_size];
            int window_index = 0;

            // 窓内の画素値を取得
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 端の画素は重複させて折り返す
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;

                    window[window_index++] = in[ny * w + nx];
                }
            }

            // 窓内の画素値をソート
            qsort(window, window_size * window_size, sizeof(double), compare);

            // 中央値を出力画像に設定
            out[y * w + x] = window[window_size * window_size / 2];
        }
    }
}

// 比較関数
int compare(const void* a, const void* b) {
    return (*(double*)a - *(double*)b);
}
