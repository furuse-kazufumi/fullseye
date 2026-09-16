void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端を処理する際、端の画素は比較対象から外す。
    // つまり、端の1画素分は無視する。

    // 画像のサイズを取得
    int size = h * w;

    // Sobel オペレータのマスク
    const double sobel_x[3][3] = {{1, 0, -1}, {2, 0, -2}, {1, 0, -1}};
    const double sobel_y[3][3] = {{1, 2, 1}, {0, 0, 0}, {-1, -2, -1}};

    // 画像の各画素に対して処理を行う
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            // Sobel オペレータを適用して勾配を計算
            double gx = 0, gy = 0;
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int idx = (y + ky) * w + (x + kx);
                    gx += in[idx] * sobel_x[ky + 1][kx + 1];
                    gy += in[idx] * sobel_y[ky + 1][kx + 1];
                }
            }

            // 勾配の方向を計算
            double dir = atan2(gy, gx) * 180 / M_PI;
            if (dir < 0) dir += 180;

            // 方向を 45° 刻みの 4 区分に量子化
            int dir_quantized = (int)(dir / 45) % 4;

            // 隣接する画素との比較
            double mag = hypot(gx, gy);
            double mag_left = 0, mag_right = 0;
            int x_left = x - (dir_quantized == 0 || dir_quantized == 3);
            int x_right = x + (dir_quantized == 1 || dir_quantized == 2);
            int y_left = y - (dir_quantized == 1 || dir_quantized == 2);
            int y_right = y + (dir_quantized == 0 || dir_quantized == 3);

            mag_left = hypot(in[(y_left) * w + (x_left)], in[(y_left) * w + (x_left + 1)]);
            mag_right = hypot(in[(y_right) * w + (x_right)], in[(y_right) * w + (x_right + 1)]);

            // 非最大抑制
            if (mag >= mag_left && mag >= mag_right) {
                out[y * w + x] = mag;
            } else {
                out[y * w + x] = 0;
            }
        }
    }

    // 最大値を計算
    double max_val = 0;
    for (int i = 0; i < size; i++) {
        if (out[i] > max_val) max_val = out[i];
    }

    // 正規化
    for (int i = 0; i < size; i++) {
        out[i] /= max_val;
        if (out[i] < a * 0.3) out[i] = 0;
    }
}
