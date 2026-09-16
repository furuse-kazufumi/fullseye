#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a: -20°〜+20°の範囲を0.1〜0.9にマッピング。b: シアー量を0.1〜0.9で制御。
    double angle = (a - 0.5) * 40.0 * M_PI / 180.0; // 回転角をラジアンに変換
    double shear = (b - 0.5) * 2.0; // シアー量を-1.0〜+1.0にマッピング

    // アフィン変換行列の定義
    double cos_theta = cos(angle);
    double sin_theta = sin(angle);
    double affine_matrix[6] = {cos_theta, -sin_theta, shear * sin_theta, sin_theta, cos_theta, 0.0};

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // アフィン変換の適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] > 0.5) { // 入力画像の画素が領域に属する場合
                // アフィン変換の適用
                double new_x = affine_matrix[0] * x + affine_matrix[1] * y + affine_matrix[2];
                double new_y = affine_matrix[3] * x + affine_matrix[4] * y + affine_matrix[5];

                // 新しい座標が画像の範囲内にあるかチェック
                if (new_x >= 0 && new_x < w && new_y >= 0 && new_y < h) {
                    // 二値化
                    out[(int)new_y * w + (int)new_x] = (new_x == (int)new_x && new_y == (int)new_y) ? 1.0 : 0.0;
                }
            }
        }
    }
}
