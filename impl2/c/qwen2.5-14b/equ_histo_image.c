void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ヒストグラムの初期化
    int histogram[256] = {0};
    int total_pixels = h * w;

    // ヒストグラムの計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int pixel_value = (int)(in[y * w + x] * 255.0);
            histogram[pixel_value]++;
        }
    }

    // 累積分布関数の計算
    int cumulative_distribution[256] = {0};
    cumulative_distribution[0] = histogram[0];
    for (int i = 1; i < 256; i++) {
        cumulative_distribution[i] = cumulative_distribution[i - 1] + histogram[i];
    }

    // ヒストグラム平坦化の適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int pixel_value = (int)(in[y * w + x] * 255.0);
            int new_pixel_value = (cumulative_distribution[pixel_value] * 255) / total_pixels;
            out[y * w + x] = new_pixel_value / 255.0;
        }
    }
}
