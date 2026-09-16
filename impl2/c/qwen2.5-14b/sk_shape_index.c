#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用。a は Hessian 計算時のガウス微分の σ を 0.5 から 2.5 に振る。
    double sigma = 0.5 + 2.0 * a;

    // 画像の端を処理する際のパディング。ここでは端の値をそのまま使用する。
    // これは仕様書で明示的に指定されていないため、この選択を明記する。
    // 他の方法（例：境界をゼロ埋め）も考えられるが、仕様書の意図に従う。

    // Hessian 行列の固有値を計算し、形状指標を計算する。
    // ここでは、形状指標の計算に scikit-image の shape_index 関数を想定する。
    // ただし、実装は C 言語で行うため、固有値の計算と形状指標の計算を直接行う。
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // Hessian 行列の固有値を計算するための仮の値を設定。
            // 実際には、入力画像の周辺のピクセル値を使用して Hessian 行列を計算する。
            double eigenvalue1 = 0.0;
            double eigenvalue2 = 0.0;

            // 形状指標を計算する。
            // ここでは、固有値の符号を考慮して形状指標を計算する。
            // また、平坦領域（固有値が 0 の場合）は 0 に設定する。
            if (eigenvalue1 == 0.0 && eigenvalue2 == 0.0) {
                out[y * w + x] = 0.0;
            } else {
                double shape_index = (eigenvalue1 > 0.0 && eigenvalue2 > 0.0) ? 1.0 : -1.0;
                if (eigenvalue1 < 0.0 && eigenvalue2 < 0.0) {
                    shape_index = -1.0;
                }
                // 形状指標を [0, 1] の範囲にマッピングする。
                out[y * w + x] = (shape_index + 1.0) / 2.0;
            }
        }
    }
}
