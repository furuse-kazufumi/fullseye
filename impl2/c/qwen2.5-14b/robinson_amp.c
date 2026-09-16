void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double kernel[8][3] = {
        {-1, 0, 0}, {0, -1, 0}, {1, 0, 0}, {0, 1, 0},
        {-1, -1, 0}, {1, -1, 0}, {-1, 1, 0}, {1, 1, 0}
    };
    const int kernel_size = 8;

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 端の処理: 端画素を重複させて折り返す
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_val = 0.0;
            for (int k = 0; k < kernel_size; k++) {
                int ky = y + kernel[k][1];
                int kx = x + kernel[k][0];
                // 端の処理: 端画素を重複させて折り返す
                if (ky < 0) ky = -ky;
                if (ky >= h) ky = 2 * h - ky - 1;
                if (kx < 0) kx = -kx;
                if (kx >= w) kx = 2 * w - kx - 1;
                double val = in[ky * w + kx];
                double abs_val = fabs(val);
                if (abs_val > max_val) {
                    max_val = abs_val;
                }
            }
            out[y * w + x] = max_val;
        }
    }

    // 出力を最大値で正規化
    double max_out = 0.0;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (out[y * w + x] > max_out) {
                max_out = out[y * w + x];
            }
        }
    }
    if (max_out > 0.0) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                out[y * w + x] /= max_out;
            }
        }
    }
}
