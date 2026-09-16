void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 単調性を計算するための内部関数
    double monotony_at(const double* img, int y, int x, int height, int width) {
        int count = 0;
        for (int dy = -1; dy <= 1; dy++) {
            for (int dx = -1; dx <= 1; dx++) {
                if (dx == 0 && dy == 0) continue; // 中心の画素はカウントしない
                int ny = (y + dy + height) % height; // 周期的境界処理
                int nx = (x + dx + width) % width;
                if (img[ny * width + nx] < img[y * width + x]) {
                    count++;
                }
            }
        }
        return count / 8.0; // 8近傍のうち、中心画素より小さい画素の割合を返す
    }

    // 出力画像の最大値を計算するための変数
    double max_out = 0.0;

    // 出力画像の各画素を計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double value = monotony_at(in, y, x, h, w);
            out[y * w + x] = value;
            if (value > max_out) {
                max_out = value;
            }
        }
    }

    // 出力画像を最大値で正規化
    for (int i = 0; i < h * w; i++) {
        out[i] /= max_out;
    }
}
