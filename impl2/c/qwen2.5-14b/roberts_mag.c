void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。コメントアウトしておく。
    (void)a;
    (void)b;

    // 画像の端をレプリケートで処理する。これは仕様書で明示的に指定されている。
    // 画像の各ピクセルに対して Roberts クロスフィルタを適用する。
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // Roberts クロスフィルタの適用
            double dx = in[(y < h - 1 && x < w - 1) ? (y + 1) * w + x + 1 : 0] - in[y * w + x];
            double dy = in[(y < h - 1 && x > 0) ? (y + 1) * w + x - 1 : 0] - in[y * w + x - 1];
            double gradient = sqrt(dx * dx + dy * dy);

            // 出力をその画像の最大値で正規化する。
            out[y * w + x] = gradient;
        }
    }

    // 正規化のため、画像全体の最大値を計算する。
    double max_val = 0.0;
    for (int i = 0; i < h * w; ++i) {
        if (out[i] > max_val) {
            max_val = out[i];
        }
    }

    // 最大値が 0 の場合、全てのピクセルを 0 に設定する。
    if (max_val > 0.0) {
        for (int i = 0; i < h * w; ++i) {
            out[i] /= max_val;
        }
    }
}
