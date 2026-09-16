#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端を処理する方法: OpenCV の BORDER_REFLECT_101 に従う
    // つまり、端画素を重複させずに折り返す (d c b | a b c d)

    // Sobel カーネルのサイズ
    const int ksize = 3;
    const int half_ksize = ksize / 2;

    // Sobel カーネル
    const double sobel_x[3][3] = {
        {-1, 0, 1},
        {-2, 0, 2},
        {-1, 0, 1}
    };
    const double sobel_y[3][3] = {
        {-1, -2, -1},
        { 0,  0,  0},
        { 1,  2,  1}
    };

    // 出力画像の最大値を求めるための変数
    double max_val = 0.0;

    // 各画素に対して処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double Ixx = 0.0, Ixy = 0.0, Iyy = 0.0;

            // Sobel 畳み込みを用いて Ixx, Ixy, Iyy を計算
            for (int ky = -half_ksize; ky <= half_ksize; ky++) {
                for (int kx = -half_ksize; kx <= half_ksize; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // 境界外アクセスを防ぐための折り返し処理
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;

                    double pixel = in[ny * w + nx];
                    double dx = sobel_x[ky + half_ksize][kx + half_ksize] * pixel;
                    double dy = sobel_y[ky + half_ksize][kx + half_ksize] * pixel;

                    Ixx += dx * dx;
                    Ixy += dx * dy;
                    Iyy += dy * dy;
                }
            }

            // コーナー検出のための行列式を計算
            double det = Ixx * Iyy - Ixy * Ixy;
            double trace = Ixx + Iyy;
            double response = det - 0.04 * trace * trace;

            // 出力画像に値を書き込む
            out[y * w + x] = response;

            // 最大値を更新
            if (response > max_val) {
                max_val = response;
            }
        }
    }

    // 出力を最大値で正規化
    if (max_val > 0.0) {
        for (int i = 0; i < h * w; i++) {
            out[i] /= max_val;
        }
    }
}
