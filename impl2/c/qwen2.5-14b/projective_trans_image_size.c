#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 射影変換のパラメータを計算
    double scale = 1.0 - a; // 歪みのスケール
    double skew = b - 0.5; // 非対称性のスケール

    // 射影変換の行列を計算
    double A[6] = {
        scale, skew, 0.0,
        -skew, scale, 0.0,
        0.0, 0.0, 1.0
    };

    // 射影変換を適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 射影変換後の座標を計算
            double x_new = A[0] * x + A[1] * y + A[2];
            double y_new = A[3] * x + A[4] * y + A[5];

            // 射影変換後の座標が画像の範囲内にあるかチェック
            if (x_new >= 0 && x_new < w && y_new >= 0 && y_new < h) {
                // 射影変換後の座標から出力画像のインデックスを計算
                int idx = (int)y_new * w + (int)x_new;
                // 出力画像に値をコピー
                out[idx] = in[y * w + x];
            } else {
                // 射影変換後の座標が画像の範囲外の場合、出力画像の該当位置には入力画像の値をコピーしない
                // ここでは、範囲外の場合は出力画像の該当位置を 0 に設定する
                out[y * w + x] = 0.0;
            }
        }
    }
}
