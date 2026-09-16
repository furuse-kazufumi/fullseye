void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double h_depth = 0.02 + a * 0.3; // h-minima の深さ
    const int size = h * w; // 入力画像のサイズ

    // 出力画像を初期化
    for (int i = 0; i < size; i++) {
        out[i] = 0.0;
    }

    // Sobel オペレータの定義
    const int sobel_x[3][3] = {{-1, 0, 1}, {-2, 0, 2}, {-1, 0, 1}};
    const int sobel_y[3][3] = {{-1, -2, -1}, {0, 0, 0}, {1, 2, 1}};

    // 勾配画像の計算
    double gradient[size];
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double gx = 0.0, gy = 0.0;
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    gx += sobel_x[ky + 1][kx + 1] * in[(y + ky) * w + (x + kx)];
                    gy += sobel_y[ky + 1][kx + 1] * in[(y + ky) * w + (x + kx)];
                }
            }
            gradient[y * w + x] = sqrt(gx * gx + gy * gy);
        }
    }

    // h-minima マーカーの生成
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double minima = 1.0;
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    if (gradient[(y + ky) * w + (x + kx)] < minima) {
                        minima = gradient[(y + ky) * w + (x + kx)];
                    }
                }
            }
            if (gradient[y * w + x] <= minima + h_depth) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
