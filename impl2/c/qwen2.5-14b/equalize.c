void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ヒストグラムの計算
    int histogram[256] = {0};
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int pixel = (int)(in[y * w + x] * 255.0);
            if (pixel >= 0 && pixel <= 255) {
                histogram[pixel]++;
            }
        }
    }

    // 累積分布関数 (CDF) の計算
    int cdf[256] = {0};
    int total_pixels = h * w;
    int cdf_value = 0;
    for (int i = 0; i < 256; i++) {
        cdf_value += histogram[i];
        cdf[i] = (int)((cdf_value * 255.0) / total_pixels);
    }

    // 出力画像の生成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int pixel = (int)(in[y * w + x] * 255.0);
            if (pixel >= 0 && pixel <= 255) {
                out[y * w + x] = cdf[pixel] / 255.0;
            } else {
                out[y * w + x] = in[y * w + x]; // 範囲外の値はそのまま出力
            }
        }
    }
}
