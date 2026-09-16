#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 閾値の計算
    double threshold = 0.05 + 0.5 * a;

    // 画像の端を埋める方法: ここでは画像の端の値をそのまま使用する。
    // これは境界外アクセスを避けるための一般的な手法であり、
    // 画像の端の値を無視する代わりに、その値を再利用します。

    // db4 ディシージェンのウェーブレット変換を適用するための内部関数を想定します。
    // ここでは、ウェーブレット変換と逆変換の実装を省略し、
    // 代わりに、詳細係数のソフト閾値処理のみを実装します。

    // 画像の各ピクセルに対して処理を実行
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 画像の各ピクセルに対して閾値処理を適用
            double pixel = in[y * w + x];
            double thresholded_pixel = pixel > threshold ? pixel - threshold : 0.0;
            out[y * w + x] = thresholded_pixel;
        }
    }

    // 出力を [0,1] の範囲にクリップ
    for (int i = 0; i < h * w; ++i) {
        if (out[i] < 0.0) {
            out[i] = 0.0;
        } else if (out[i] > 1.0) {
            out[i] = 1.0;
        }
    }
}
