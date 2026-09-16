void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // PSF のガウシアン形状のパラメータを計算
    double sigma = 0.5 + 1.5 * a;
    double balance = 0.05 + 0.5 * b;

    // ガウシアンカーネルの生成
    int kernel_size = 5;
    double kernel[kernel_size * kernel_size];
    double sum = 0.0;
    for (int ky = 0; ky < kernel_size; ky++) {
        for (int kx = 0; kx < kernel_size; kx++) {
            int y = ky - kernel_size / 2;
            int x = kx - kernel_size / 2;
            kernel[ky * kernel_size + kx] = exp(-(x * x + y * y) / (2 * sigma * sigma));
            sum += kernel[ky * kernel_size + kx];
        }
    }
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        kernel[i] /= sum;
    }

    // 画像のフィルタリング
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double filtered_value = 0.0;
            for (int ky = 0; ky < kernel_size; ky++) {
                for (int kx = 0; kx < kernel_size; kx++) {
                    int ky_wrap = (y + ky - kernel_size / 2 + h) % h;
                    int kx_wrap = (x + kx - kernel_size / 2 + w) % w;
                    filtered_value += in[ky_wrap * w + kx_wrap] * kernel[ky * kernel_size + kx];
                }
            }
            out[y * w + x] = filtered_value / (1 + balance * (filtered_value - 1));
        }
    }
}
