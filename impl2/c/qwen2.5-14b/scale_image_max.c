void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の最小値と最大値を計算
    double min_val = in[0];
    double max_val = in[0];
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double val = in[y * w + x];
            if (val < min_val) {
                min_val = val;
            }
            if (val > max_val) {
                max_val = val;
            }
        }
    }

    // 最小値と最大値が同じ場合、全てのピクセルを 0 に設定
    if (min_val == max_val) {
        for (int i = 0; i < h * w; ++i) {
            out[i] = 0.0;
        }
        return;
    }

    // 出力画像の生成
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double val = in[y * w + x];
            out[y * w + x] = (val - min_val) / (max_val - min_val);
        }
    }
}
