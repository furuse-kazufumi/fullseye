#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像のサイズを取得
    int size = h * w;
    // 出力画像を初期化
    memset(out, 0, size * sizeof(double));

    // ラドン変換の角度の数を決定
    int num_angles = 180; // 0から180度まで等間隔に分割
    double angle_step = M_PI / num_angles; // 角度のステップ

    // ラドン変換の実行
    for (int angle_idx = 0; angle_idx < num_angles; angle_idx++) {
        double angle = angle_idx * angle_step;
        double cos_theta = cos(angle);
        double sin_theta = sin(angle);

        // 各角度での投影データを計算
        for (int t = 0; t < w + h - 1; t++) {
            double max_val = 0.0;
            for (int y = 0; y < h; y++) {
                for (int x = 0; x < w; x++) {
                    double t_val = x * cos_theta + y * sin_theta - t;
                    if (fabs(t_val) < 1e-6) {
                        max_val = fmax(max_val, in[y * w + x]);
                    }
                }
            }
            // 出力画像に投影データを追加
            int idx = (angle_idx * (w + h - 1) + t) % size;
            out[idx] += max_val;
        }
    }

    // 出力を最大値で正規化
    double max_out = 0.0;
    for (int i = 0; i < size; i++) {
        max_out = fmax(max_out, out[i]);
    }
    if (max_out > 0.0) {
        for (int i = 0; i < size; i++) {
            out[i] /= max_out;
        }
    }
}
