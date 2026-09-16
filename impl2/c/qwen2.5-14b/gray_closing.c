void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素のサイズを決定
    int kernel_size = 3; // デフォルト値
    if (a >= 0.75) {
        kernel_size = 9;
    } else if (a >= 0.49) {
        kernel_size = 7;
    } else if (a >= 0.25) {
        kernel_size = 5;
    }

    // クロージングのための内部関数
    void dilation(const double* img, int h, int w, int kernel_size, double* result) {
        int radius = kernel_size / 2;
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                double max_val = img[y * w + x];
                for (int ky = -radius; ky <= radius; ++ky) {
                    for (int kx = -radius; kx <= radius; ++kx) {
                        int ny = y + ky;
                        int nx = x + kx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            max_val = fmax(max_val, img[ny * w + nx]);
                        }
                    }
                }
                result[y * w + x] = max_val;
            }
        }
    }

    void erosion(const double* img, int h, int w, int kernel_size, double* result) {
        int radius = kernel_size / 2;
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                double min_val = img[y * w + x];
                for (int ky = -radius; ky <= radius; ++ky) {
                    for (int kx = -radius; kx <= radius; ++kx) {
                        int ny = y + ky;
                        int nx = x + kx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            min_val = fmin(min_val, img[ny * w + nx]);
                        }
                    }
                }
                result[y * w + x] = min_val;
            }
        }
    }

    // 一時的な画像領域を確保
    double* temp = (double*)malloc(h * w * sizeof(double));
    if (temp == NULL) {
        return; // メモリ確保失敗
    }

    // 膨張処理
    dilation(in, h, w, kernel_size, temp);

    // 収縮処理
    erosion(temp, h, w, kernel_size, out);

    // 一時領域を解放
    free(temp);
}
