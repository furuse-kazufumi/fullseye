void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の中心座標
    int center_x = w / 2;
    int center_y = h / 2;

    // 画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // ピクセルの中心からの距離を計算
            double dx = x - center_x;
            double dy = y - center_y;
            double r = sqrt(dx * dx + dy * dy);

            // フォールオフ半径を計算
            double R = 0.35 + 1.15 * b;

            // コサインの4乗の法則を適用
            double transmission = 1.0 / (1.0 + (r / R) * (r / R)) / (1.0 + (r / R) * (r / R));

            // 出力を計算
            double value = in[y * w + x];
            double vignette_value = value * transmission;
            out[y * w + x] = (1.0 - a) * value + a * vignette_value;
        }
    }
}
