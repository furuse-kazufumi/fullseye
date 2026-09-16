void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double LOWER_MARGIN = 0.1 + 0.3 * a;
    const double UPPER_MARGIN = 0.1 + 0.3 * b;
    const int center_x = w / 2;
    const int center_y = h / 2;
    const double center_value = in[center_y * w + center_x];

    // 画像の中心画素をシードとして使用
    const double lower_threshold = center_value - LOWER_MARGIN;
    const double upper_threshold = center_value + UPPER_MARGIN;

    // 出力画像を初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = 0.0;
        }
    }

    // 中心画素をシードとして設定
    out[center_y * w + center_x] = 1.0;

    // 連結領域の拡張
    int changed = 1;
    while (changed) {
        changed = 0;
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                if (out[y * w + x] == 1.0) {
                    // 4近傍の画素をチェック
                    for (int dy = -1; dy <= 1; ++dy) {
                        for (int dx = -1; dx <= 1; ++dx) {
                            if (dx == 0 && dy == 0) continue;
                            int nx = x + dx;
                            int ny = y + dy;
                            if (nx < 0 || nx >= w || ny < 0 || ny >= h) continue; // 画像の境界外を無視
                            if (out[ny * w + nx] == 1.0) continue; // 既に設定された画素を無視
                            double value = in[ny * w + nx];
                            if (value >= lower_threshold && value <= upper_threshold) {
                                out[ny * w + nx] = 1.0;
                                changed = 1;
                            }
                        }
                    }
                }
            }
        }
    }
}
