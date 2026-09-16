void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 半径 r の計算
    int r = 1 + (int)(a * 4);
    int kernel_size = 2 * r + 1;

    // カーネルの作成
    double kernel[kernel_size * kernel_size];
    int kernel_center = r;
    int kernel_radius = r;
    int kernel_sum = 0;

    for (int ky = -kernel_radius; ky <= kernel_radius; ky++) {
        for (int kx = -kernel_radius; kx <= kernel_radius; kx++) {
            int k = ky * kernel_size + kx;
            if (kx * kx + ky * ky <= kernel_radius * kernel_radius) {
                kernel[k] = 1.0;
                kernel_sum += 1.0;
            } else {
                kernel[k] = 0.0;
            }
        }
    }

    // 画像の平滑化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;

            for (int ky = -kernel_radius; ky <= kernel_radius; ky++) {
                for (int kx = -kernel_radius; kx <= kernel_radius; kx++) {
                    int ky_mirror = y + ky;
                    int kx_mirror = x + kx;

                    // 鏡像法で境界を処理
                    if (ky_mirror < 0) ky_mirror = -ky_mirror - 1;
                    if (ky_mirror >= h) ky_mirror = 2 * h - ky_mirror - 1;
                    if (kx_mirror < 0) kx_mirror = -kx_mirror - 1;
                    if (kx_mirror >= w) kx_mirror = 2 * w - kx_mirror - 1;

                    int in_index = ky_mirror * w + kx_mirror;
                    int kernel_index = (ky + kernel_radius) * kernel_size + (kx + kernel_radius);
                    sum += in[in_index] * kernel[kernel_index];
                    count += kernel[kernel_index];
                }
            }

            out[y * w + x] = sum / count;
        }
    }
}
