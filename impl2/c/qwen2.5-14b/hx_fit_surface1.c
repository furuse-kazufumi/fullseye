#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は未使用パラメータであるため、無視する。

    // 画像の各ピクセルに対して、1次多項式面で最小二乗近似を行う。
    // まず、画像の各ピクセルの座標を [-1, 1] に正規化する。
    // 画像の中心座標を (cx, cy) とすると、
    // cx = (w - 1) / 2.0, cy = (h - 1) / 2.0 となる。
    double cx = (w - 1) / 2.0;
    double cy = (h - 1) / 2.0;

    // 最小二乗近似のための行列 A の初期化
    double A[3][3] = {0};
    double B[3] = {0};

    // 画像の各ピクセルに対して、行列 A とベクトル B を更新する。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double x_norm = (x - cx) / cx;
            double y_norm = (y - cy) / cy;
            double z = in[y * w + x];

            // 正規化座標を用いて行列 A とベクトル B を更新
            A[0][0] += 1;
            A[0][1] += x_norm;
            A[0][2] += y_norm;
            A[1][0] += x_norm;
            A[1][1] += x_norm * x_norm;
            A[1][2] += x_norm * y_norm;
            A[2][0] += y_norm;
            A[2][1] += y_norm * x_norm;
            A[2][2] += y_norm * y_norm;
            B[0] += z;
            B[1] += z * x_norm;
            B[2] += z * y_norm;
        }
    }

    // 行列 A の逆行列を計算し、ベクトル B との積を計算して、近似面のパラメータを求める。
    double detA = A[0][0] * (A[1][1] * A[2][2] - A[1][2] * A[2][1]) -
                  A[0][1] * (A[1][0] * A[2][2] - A[1][2] * A[2][0]) +
                  A[0][2] * (A[1][0] * A[2][1] - A[1][1] * A[2][0]);

    if (fabs(detA) < 1e-6) {
        // 行列 A が特異行列である場合、近似を失敗とする。
        for (int i = 0; i < h * w; i++) {
            out[i] = 0.0;
        }
        return;
    }

    double invA[3][3];
    invA[0][0] = (A[1][1] * A[2][2] - A[1][2] * A[2][1]) / detA;
    invA[0][1] = (A[0][2] * A[2][1] - A[0][1] * A[2][2]) / detA;
    invA[0][2] = (A[0][1] * A[1][2] - A[0][2] * A[1][1]) / detA;
    invA[1][0] = (A[1][2] * A[2][0] - A[1][0] * A[2][2]) / detA;
    invA[1][1] = (A[0][0] * A[2][2] - A[0][2] * A[2][0]) / detA;
    invA[1][2] = (A[0][2] * A[1][0] - A[0][0] * A[1][2]) / detA;
    invA[2][0] = (A[1][0] * A[2][1] - A[1][1] * A[2][0]) / detA;
    invA[2][1] = (A[0][1] * A[2][0] - A[0][0] * A[2][1]) / detA;
    invA[2][2] = (A[0][0] * A[1][1] - A[0][1] * A[1][0]) / detA;

    double params[3];
    params[0] = invA[0][0] * B[0] + invA[0][1] * B[1] + invA[0][2] * B[2];
    params[1] = invA[1][0] * B[0] + invA[1][1] * B[1] + invA[1][2] * B[2];
    params[2] = invA[2][0] * B[0] + invA[2][1] * B[1] + invA[2][2] * B[2];

    // 近似面のパラメータを用いて、各ピクセルの値を計算し、出力画像に格納する。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double x_norm = (x - cx) / cx;
            double y_norm = (y - cy) / cy;
            double z = params[0] + params[1] * x_norm + params[2] * y_norm;
            out[y * w + x] = z;
        }
    }

    // 最終的に出力を [0, 1] の範囲に正規化する。
    double min_val = out[0];
    double max_val = out[0];
    for (int i = 1; i < h * w; i++) {
        if (out[i] < min_val) {
            min_val = out[i];
        }
        if (out[i] > max_val) {
            max_val = out[i];
        }
    }
    if (max_val - min_val > 1e-6) {
        for (int i = 0; i < h * w; i++) {
            out[i] = (out[i] - min_val) / (max_val - min_val);
        }
    }
}
