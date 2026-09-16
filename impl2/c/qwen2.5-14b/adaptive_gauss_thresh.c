#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double sigma_min = 1.0;
    const double sigma_max = 4.0;
    const double offset_min = -0.15;
    const double offset_max = 0.15;

    // パラメータの範囲を調整
    double sigma = sigma_min + (sigma_max - sigma_min) * a;
    double offset = offset_min + (offset_max - offset_min) * (b - 0.5);

    // ガウシアンフィルタの初期化
    int kernel_size = (int)(6 * sigma + 1);
    if (kernel_size % 2 == 0) kernel_size++; // カーネルサイズは奇数でなければならない
    double* kernel = (double*)malloc(kernel_size * kernel_size * sizeof(double));
    double sum = 0.0;

    // ガウシアンカーネルの計算
    for (int i = -kernel_size / 2; i <= kernel_size / 2; i++) {
        for (int j = -kernel_size / 2; j <= kernel_size / 2; j++) {
            double x = i, y = j;
            kernel[(i + kernel_size / 2) * kernel_size + (j + kernel_size / 2)] = exp(-(x * x + y * y) / (2 * sigma * sigma));
            sum += kernel[(i + kernel_size / 2) * kernel_size + (j + kernel_size / 2)];
        }
    }

    // カーネルの正規化
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        kernel[i] /= sum;
    }

    // 出力画像の初期化
    for (int i = 0; i < h * w; i++) {
        out[i] = 0.0;
    }

    // ガウシアンフィルタリングとしきい値処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double filtered_value = 0.0;
            int start_y = y - kernel_size / 2;
            int start_x = x - kernel_size / 2;
            int end_y = start_y + kernel_size;
            int end_x = start_x + kernel_size;

            // カーネルの適用範囲を画像の範囲内に制限
            if (start_y < 0) start_y = 0;
            if (start_x < 0) start_x = 0;
            if (end_y > h) end_y = h;
            if (end_x > w) end_x = w;

            // ガウシアンフィルタリング
            for (int ky = start_y; ky < end_y; ky++) {
                for (int kx = start_x; kx < end_x; kx++) {
                    int index = ky * w + kx;
                    filtered_value += in[index] * kernel[(ky - start_y) * kernel_size + (kx - start_x)];
                }
            }

            // しきい値処理
            if (in[y * w + x] > filtered_value + offset) {
                out[y * w + x] = 1.0;
            }
        }
    }

    // メモリの解放
    free(kernel);
}
