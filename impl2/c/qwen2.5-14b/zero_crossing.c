void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ラプラシアンフィルタのカーネル
    double laplacian_kernel[9] = {0.0, 1.0, 0.0, 1.0, -4.0, 1.0, 0.0, 1.0, 0.0};

    // ガウス平滑化のシグマを計算
    double sigma = 0.5 + 2.0 * a;

    // ガウスカーネルのサイズを計算
    int kernel_size = (int)(3.0 * sigma + 0.5);
    if (kernel_size % 2 == 0) {
        kernel_size++;
    }

    // ガウスカーネルを計算
    double* gaussian_kernel = (double*)malloc(kernel_size * kernel_size * sizeof(double));
    for (int i = 0; i < kernel_size; i++) {
        for (int j = 0; j < kernel_size; j++) {
            double x = i - kernel_size / 2;
            double y = j - kernel_size / 2;
            gaussian_kernel[i * kernel_size + j] = exp(-(x * x + y * y) / (2.0 * sigma * sigma));
        }
    }

    // ガウスカーネルの合計を計算
    double gaussian_sum = 0.0;
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        gaussian_sum += gaussian_kernel[i];
    }

    // 出力画像を初期化
    for (int i = 0; i < h * w; i++) {
        out[i] = 0.0;
    }

    // 入力画像に対してガウスフィルタを適用
    double* temp = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        sum += in[ny * w + nx] * gaussian_kernel[(ky + kernel_size / 2) * kernel_size + (kx + kernel_size / 2)];
                    }
                }
            }
            temp[y * w + x] = sum / gaussian_sum;
        }
    }

    // ラプラシアンフィルタを適用
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double laplacian = 0.0;
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    laplacian += temp[ny * w + nx] * laplacian_kernel[(ky + 1) * 3 + (kx + 1)];
                }
            }
            if ((laplacian > 0.0 && temp[y * w + x] < 0.0) || (laplacian < 0.0 && temp[y * w + x] > 0.0)) {
                out[y * w + x] = 1.0;
            }
        }
    }

    // メモリを解放
    free(gaussian_kernel);
    free(temp);
}
