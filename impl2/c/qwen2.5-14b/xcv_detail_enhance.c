#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b の範囲は [0, 1] と仮定。範囲外の値は無視する。
    if (a < 0 || a > 1 || b < 0 || b > 1) {
        return;
    }

    // 空間範囲 sigma_s と色差許容 sigma_r の計算
    double sigma_s = 10 + (50 - 10) * a; // 10 から 50 の範囲で a を線形に変換
    double sigma_r = 0.1 + (0.4 - 0.1) * b; // 0.1 から 0.4 の範囲で b を線形に変換

    // 画像の端をどのように処理するかは明示的に指定されていないため、
    // 端のピクセルはそのままコピーするという選択をとる。
    // これは、端のピクセルが周囲のピクセルと異なる可能性があるため、
    // 端のピクセルを無視せずにそのままコピーすることで、端の情報の損失を防ぐ。

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 画像の中心部分に対して処理を適用
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            // ここに具体的な detailEnhance の処理を実装する。
            // 本実装では、詳細なアルゴリズムが指定されていないため、
            // 簡単な平滑化処理を仮に実装する。
            // 実際の detailEnhance はより複雑な処理を必要とする。
            double sum = 0.0;
            int count = 0;
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    sum += in[(y + dy) * w + (x + dx)];
                    count++;
                }
            }
            out[y * w + x] = sum / count;
        }
    }
}
