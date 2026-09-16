#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // パラメータの範囲チェック
    if (a < 0.0 || a > 1.0 || b < 0.0 || b > 1.0) {
        return; // パラメータが範囲外の場合は何もしない
    }

    // カーネルサイズと角度の計算
    int kernel_size = 2 * (int)(2 + a * 6) + 1;
    double angle = 360.0 * a * M_PI / 180.0; // 角度をラジアンに変換

    // カーネルの方向オフセット
    double offset = 2.0 * b - 1.0;

    // カーネルの中心位置
    int kernel_center = (kernel_size - 1) / 2;

    // 画像の端を0で埋める
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;

            // カーネルの各位置に対して
            for (int ky = -kernel_center; ky <= kernel_center; ky++) {
                for (int kx = -kernel_center; kx <= kernel_center; kx++) {
                    // カーネルの位置を計算
                    int ky_rotated = ky * cos(angle) - kx * sin(angle);
                    int kx_rotated = ky * sin(angle) + kx * cos(angle);

                    // カーネルの位置をオフセット
                    ky_rotated += offset * (kernel_size - 1) / 2;
                    kx_rotated += offset * (kernel_size - 1) / 2;

                    // 画像の範囲内に収まるかチェック
                    if (ky_rotated >= -kernel_center && ky_rotated <= kernel_center &&
                        kx_rotated >= -kernel_center && kx_rotated <= kernel_center) {
                        int iy = y + ky_rotated;
                        int ix = x + kx_rotated;

                        // 画像の範囲内に収まるかチェック
                        if (iy >= 0 && iy < h && ix >= 0 && ix < w) {
                            sum += in[iy * w + ix];
                            count++;
                        }
                    }
                }
            }

            // 平均値を計算
            out[y * w + x] = (count > 0) ? sum / count : 0.0;
        }
    }
}
