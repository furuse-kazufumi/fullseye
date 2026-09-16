void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は半径のパラメータとして使用され、b は無視される。
    // 半径は画像の最小寸法の 10% から 50% までを想定。a が 0.5 の場合、半径は min(h, w) * 0.5 * 0.5 = min(h, w) * 0.25 となる。
    double radius = MIN(h, w) * 0.1 + a * 0.4 * MIN(h, w); // 0.1 から 0.5 の範囲に a をマッピング

    // 画像の中心座標を計算
    int center_x = w / 2;
    int center_y = h / 2;

    // 出力画像を初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = 0.0; // 初期値は 0.0 (外部)
        }
    }

    // 円の内部を 1.0 に設定
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // ピクセル (x, y) から中心までの距離を計算
            double distance = sqrt((x - center_x) * (x - center_x) + (y - center_y) * (y - center_y));
            if (distance <= radius) {
                out[y * w + x] = 1.0; // 円の内部は 1.0
            }
        }
    }
}
