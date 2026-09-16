void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は半径のスケーリングパラメータ。半径は 1 から 4 まで変化する。
    int radius = 1 + (int)(a * 3);
    int kernel_size = 2 * radius + 1;

    // データの範囲を確認し、必要に応じて補間する。
    // 画像の端は、端の画素値を用いて補間する。
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double min_val = in[y * w + x];
            double max_val = in[y * w + x];

            // 局所近傍の最大値と最小値を計算
            for (int ky = -radius; ky <= radius; ++ky) {
                for (int kx = -radius; kx <= radius; ++kx) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // 画像の範囲外の場合は端の画素値を用いる
                    if (ny < 0 || ny >= h || nx < 0 || nx >= w) {
                        continue;
                    }

                    double val = in[ny * w + nx];
                    if (val < min_val) {
                        min_val = val;
                    }
                    if (val > max_val) {
                        max_val = val;
                    }
                }
            }

            // 画素を局所近傍の最大値または最小値に置き換える
            double mid_val = (min_val + max_val) / 2.0;
            if (in[y * w + x] < mid_val) {
                out[y * w + x] = min_val;
            } else {
                out[y * w + x] = max_val;
            }
        }
    }
}
