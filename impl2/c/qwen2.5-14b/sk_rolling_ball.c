void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 球の半径を計算
    int radius = 5 + (int)(a * 20);
    // 球の直径
    int diameter = 2 * radius + 1;

    // 中心座標の計算
    int center = radius;

    // フィルタリング処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double max_value = -1.0; // 最大値を初期化

            // 球の範囲内を走査
            for (int dy = -center; dy <= center; ++dy) {
                for (int dx = -center; dx <= center; ++dx) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 画像の範囲外を無視
                    if (ny < 0 || ny >= h || nx < 0 || nx >= w) {
                        continue;
                    }

                    // 球の表面の最大値を計算
                    double distance = sqrt(dx * dx + dy * dy);
                    double surface_value = in[ny * w + nx] - distance;
                    if (surface_value > max_value) {
                        max_value = surface_value;
                    }
                }
            }

            // 元の画像から背景を引き算
            double result = in[y * w + x] - max_value;
            // 結果をクリップ
            out[y * w + x] = result < 0 ? 0 : result > 1 ? 1 : result;
        }
    }
}
