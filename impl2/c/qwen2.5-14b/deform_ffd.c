#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // n x n の格子のサイズを計算
    int n = 2 + (int)(6 * b);
    // 格子の幅と高さ
    int grid_w = n + 2;
    int grid_h = n + 2;
    // 画像の幅と高さ
    int img_w = w;
    int img_h = h;
    // 画像の各ピクセルに対する変形ベクトル
    double dx[img_h][img_w];
    double dy[img_h][img_w];
    // B-spline ベースの自由形状変形の計算
    for (int y = 0; y < img_h; y++) {
        for (int x = 0; x < img_w; x++) {
            // ピクセルの座標を格子の座標に変換
            double u = (x + 0.5) / img_w * (grid_w - 1);
            double v = (y + 0.5) / img_h * (grid_h - 1);
            // B-spline ベースの自由形状変形の計算
            double dx_sum = 0, dy_sum = 0;
            for (int j = 0; j < 4; j++) {
                for (int i = 0; i < 4; i++) {
                    double weight = bspline(u - (j + 1), 3) * bspline(v - (i + 1), 3);
                    dx_sum += weight * (sin(2 * M_PI * (j + 1) / grid_w) * a * 0.45 * fmin(img_w, img_h));
                    dy_sum += weight * (cos(2 * M_PI * (i + 1) / grid_h) * a * 0.45 * fmin(img_w, img_h));
                }
            }
            dx[y][x] = dx_sum;
            dy[y][x] = dy_sum;
        }
    }
    // 画像の各ピクセルに対する変形後の座標を計算
    for (int y = 0; y < img_h; y++) {
        for (int x = 0; x < img_w; x++) {
            double u = x + dx[y][x];
            double v = y + dy[y][x];
            // Bilinear interpolation によるリサンプリング
            double u0 = floor(u);
            double u1 = u0 + 1;
            double v0 = floor(v);
            double v1 = v0 + 1;
            double w00 = (u1 - u) * (v1 - v);
            double w01 = (u1 - u) * (v - v0);
            double w10 = (u - u0) * (v1 - v);
            double w11 = (u - u0) * (v - v0);
            double out_value = w00 * in[(int)v0 * img_w + (int)u0] +
                               w01 * in[(int)v0 * img_w + (int)u1] +
                               w10 * in[(int)v1 * img_w + (int)u0] +
                               w11 * in[(int)v1 * img_w + (int)u1];
            // 出力画像に書き込み
            out[y * img_w + x] = out_value;
        }
    }
}

// B-spline の計算
double bspline(double t, int order) {
    if (order == 0) {
        return t >= 0 && t < 1 ? 1 : 0;
    } else {
        double sum = 0;
        for (int i = 0; i <= order; i++) {
            double b = pow(-1, i) * comb(order, i) * pow(t - i, order);
            sum += b;
        }
        return sum;
    }
}

// 組み合わせの計算
double comb(int n, int k) {
    double result = 1;
    for (int i = 1; i <= k; i++) {
        result *= (n - i + 1) / (double)i;
    }
    return result;
}
