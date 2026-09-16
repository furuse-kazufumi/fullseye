#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓幅の計算
    int window_size = 5 + 2 * (int)(a * 4);
    // 窓幅が画像の高さや幅を超えないように制限
    if (window_size > h) window_size = h;
    if (window_size > w) window_size = w;
    // 窓幅が奇数であることを確認
    if (window_size % 2 == 0) window_size--;

    // 辺の処理: 窓が画像の端に達した場合、窓のサイズを端のピクセル数に合わせる
    // ここでは端のピクセル数を窓サイズとする
    int half_window = window_size / 2;

    // 2次多項式の係数を計算するための配列
    double coefficients[3];
    double x_values[window_size];
    double y_values[window_size];

    // 画像の各ピクセルに対して処理を実行
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 窓の範囲を計算
            int start_x = x - half_window;
            int end_x = x + half_window + 1;
            int start_y = y - half_window;
            int end_y = y + half_window + 1;

            // 窓の範囲が画像の外に出ないように調整
            if (start_x < 0) start_x = 0;
            if (end_x > w) end_x = w;
            if (start_y < 0) start_y = 0;
            if (end_y > h) end_y = h;

            // 窓内のピクセルを取得
            int window_width = end_x - start_x;
            int window_height = end_y - start_y;
            int window_size_adjusted = window_width * window_height;
            for (int i = 0, j = start_y * w + start_x; i < window_size_adjusted; i++, j++) {
                x_values[i] = (i % window_width) - half_window;
                y_values[i] = in[j];
            }

            // 2次多項式の係数を計算
            double sum_x = 0, sum_x2 = 0, sum_x3 = 0, sum_x4 = 0, sum_y = 0, sum_xy = 0, sum_x2y = 0;
            for (int i = 0; i < window_size_adjusted; i++) {
                sum_x += x_values[i];
                sum_x2 += x_values[i] * x_values[i];
                sum_x3 += x_values[i] * x_values[i] * x_values[i];
                sum_x4 += x_values[i] * x_values[i] * x_values[i] * x_values[i];
                sum_y += y_values[i];
                sum_xy += x_values[i] * y_values[i];
                sum_x2y += x_values[i] * x_values[i] * y_values[i];
            }

            double A[3][4] = {
                {sum_x2, sum_x, window_size_adjusted, sum_xy},
                {sum_x3, sum_x2, sum_x, sum_x2y},
                {sum_x4, sum_x3, sum_x2, sum_y}
            };

            // 係数を計算
            coefficients[0] = (A[1][3] * A[2][2] - A[2][3] * A[1][2]) / (A[0][0] * (A[1][1] * A[2][2] - A[2][1] * A[1][2]) - A[0][1] * (A[1][0] * A[2][2] - A[2][0] * A[1][2]) + A[0][2] * (A[1][0] * A[2][1] - A[2][0] * A[1][1]));
            coefficients[1] = (A[0][3] * A[2][2] - A[2][3] * A[0][2]) / (A[1][0] * (A[2][1] * A[0][2] - A[0][1] * A[2][2]) - A[1][1] * (A[2][0] * A[0][2] - A[0][0] * A[2][2]) + A[1][2] * (A[2][0] * A[0][1] - A[0][0] * A[2][1]));
            coefficients[2] = (A[0][3] * A[1][2] - A[1][3] * A[0][2]) / (A[2][0] * (A[0][1] * A[1][2] - A[1][1] * A[0][2]) - A[2][1] * (A[0][0] * A[1][2] - A[1][0] * A[0][2]) + A[2][2] * (A[0][0] * A[1][1] - A[1][0] * A[0][1]));

            // 中心のピクセルの値を更新
            out[y * w + x] = coefficients[0] + coefficients[1] * 0 + coefficients[2] * 0 * 0;
        }
    }
}
