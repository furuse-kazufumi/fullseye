void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double PI = 3.14159265358979323846;
    const int max_angle = 180; // 最大角度 (度)
    const int num_angles = 180; // 使用する角度の数 (180 度間隔で分割)

    // 角度の範囲を計算
    int span = (int)(max_angle * (0.25 + 0.75 * a));

    // 出力画像の高さと幅を計算
    int out_h = span;
    int out_w = w;

    // 出力画像の最大値を初期化
    double max_val = 0.0;

    // Radon 変換を適用
    for (int angle = 0; angle < out_h; ++angle) {
        double theta = (double)angle / (out_h - 1) * span * PI / 180.0;
        for (int x = 0; x < out_w; ++x) {
            double sum = 0.0;
            for (int y = 0; y < h; ++y) {
                double x_proj = x + (y - (h - 1) / 2.0) * tan(theta);
                int x_idx = (int)round(x_proj);
                if (x_idx >= 0 && x_idx < w) {
                    sum += in[y * w + x_idx];
                }
            }
            out[angle * out_w + x] = sum;
            if (sum > max_val) {
                max_val = sum;
            }
        }
    }

    // 出力画像を正規化
    if (max_val > 0.0) {
        for (int i = 0; i < out_h * out_w; ++i) {
            out[i] /= max_val;
        }
    }
}
