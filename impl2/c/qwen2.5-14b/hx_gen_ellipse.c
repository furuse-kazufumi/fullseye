void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 楕円の中心を画像の中心に設定
    int center_x = w / 2;
    int center_y = h / 2;

    // 楕円の半径を計算
    int radius_x = (int)(w * a * 0.5);
    int radius_y = (int)(h * b * 0.5);

    // 画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // ピクセルの位置から楕円の方程式を計算
            double dx = (x - center_x) * (x - center_x) / (radius_x * radius_x);
            double dy = (y - center_y) * (y - center_y) / (radius_y * radius_y);
            double distance = dx + dy;

            // 方程式の結果が 1 より小さい場合、楕円内と判定
            out[y * w + x] = (distance < 1.0) ? 1.0 : 0.0;
        }
    }
}
