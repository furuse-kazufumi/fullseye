void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double cutoff = 0.05 + 0.45 * a; // 周波数カットオフ
    const int hw = h * w; // 全体のピクセル数

    // 出力画像の初期化
    for (int i = 0; i < hw; ++i) {
        out[i] = 0.0;
    }

    // 各ピクセルに対して処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 正規化周波数の計算
            double fy = (y - h / 2.0) / (h / 2.0);
            double fx = (x - w / 2.0) / (w / 2.0);

            // 半径の計算
            double r = sqrt(fy * fy + fx * fx);

            // マスクの適用
            if (r <= cutoff) {
                out[y * w + x] = in[y * w + x];
            }
        }
    }
}
