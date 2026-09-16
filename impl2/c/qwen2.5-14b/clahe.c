void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const int MAX_TILES = 100; // 最大タイル数
    const int BIN_COUNT = 256; // ヒストグラムのビン数
    const double CLIP_LIMIT_MULTIPLIER = pow(256, b); // クリップリミットの倍率

    // タイル数の計算
    int nb = 2 + (int)(3 * a); // タイル数
    int tile_h = h / nb; // 各タイルの高さ
    int tile_w = w / nb; // 各タイルの幅

    // 各タイルのヒストグラムとCDFを計算
    double histograms[MAX_TILES][BIN_COUNT] = {0};
    double cdfs[MAX_TILES][BIN_COUNT] = {0};
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int tile_y = y / tile_h;
            int tile_x = x / tile_w;
            int tile_index = tile_y * nb + tile_x;
            int bin = (int)(in[y * w + x] * BIN_COUNT);
            histograms[tile_index][bin]++;
        }
    }

    // 各タイルのCDFを計算
    for (int tile_index = 0; tile_index < nb * nb; tile_index++) {
        double total = 0;
        for (int bin = 0; bin < BIN_COUNT; bin++) {
            total += histograms[tile_index][bin];
            cdfs[tile_index][bin] = total;
        }
    }

    // 各タイルのCDFをクリップリミットで制限
    for (int tile_index = 0; tile_index < nb * nb; tile_index++) {
        double max_count = 0;
        for (int bin = 0; bin < BIN_COUNT; bin++) {
            max_count = fmax(max_count, histograms[tile_index][bin]);
        }
        double clip_limit = max_count * CLIP_LIMIT_MULTIPLIER;
        for (int bin = 0; bin < BIN_COUNT; bin++) {
            cdfs[tile_index][bin] = fmin(cdfs[tile_index][bin], clip_limit);
        }
    }

    // 各タイルのCDFをヒストグラム等化のCDFに変換
    for (int tile_index = 0; tile_index < nb * nb; tile_index++) {
        double total = 0;
        for (int bin = 0; bin < BIN_COUNT; bin++) {
            total += cdfs[tile_index][bin];
            cdfs[tile_index][bin] = total / (tile_h * tile_w);
        }
    }

    // 出力画像を計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int tile_y = y / tile_h;
            int tile_x = x / tile_w;
            int tile_index = tile_y * nb + tile_x;
            int bin = (int)(in[y * w + x] * BIN_COUNT);
            double cdf_value = cdfs[tile_index][bin];
            double cdf_value_left = cdf_value;
            double cdf_value_right = cdf_value;
            double cdf_value_top = cdf_value;
            double cdf_value_bottom = cdf_value;

            // 線形補間
            if (tile_y > 0) {
                cdf_value_top = cdfs[(tile_y - 1) * nb + tile_x][bin];
            }
            if (tile_y < nb - 1) {
                cdf_value_bottom = cdfs[(tile_y + 1) * nb + tile_x][bin];
            }
            if (tile_x > 0) {
                cdf_value_left = cdfs[tile_y * nb + tile_x - 1][bin];
            }
            if (tile_x < nb - 1) {
                cdf_value_right = cdfs[tile_y * nb + tile_x + 1][bin];
            }

            double weight_top = (tile_y + 1) * tile_h - y;
            double weight_bottom = y - tile_y * tile_h;
            double weight_left = (tile_x + 1) * tile_w - x;
            double weight_right = x - tile_x * tile_w;

            double interpolated_value = (weight_top * cdf_value_top + weight_bottom * cdf_value_bottom + weight_left * cdf_value_left + weight_right * cdf_value_right) / (tile_h * tile_w);
            out[y * w + x] = interpolated_value / BIN_COUNT;
        }
    }
}
