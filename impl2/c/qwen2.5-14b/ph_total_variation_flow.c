#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 辺の境界をどのように処理するか: ここでは、境界の値をそのまま使用する。
    // これは、境界の値が入力画像の値を反映していると仮定しています。

    // フィルタリングのステップ数とフィデリティ重み
    int steps = (int)(a * 100); // 0.1 から 1.0 の範囲を 100 ステップに分割
    double lambda = b; // フィデリティ重み

    // 画像の各ピクセルに対して処理を行う
    for (int step = 0; step < steps; step++) {
        double* temp = (double*)malloc(h * w * sizeof(double));
        if (temp == NULL) {
            // メモリ確保失敗時の処理
            return;
        }

        // 勾配の計算
        for (int y = 1; y < h - 1; y++) {
            for (int x = 1; x < w - 1; x++) {
                double dx = in[(y + 1) * w + x] - in[(y - 1) * w + x];
                double dy = in[y * w + (x + 1)] - in[y * w + (x - 1)];
                double grad_norm = sqrt(dx * dx + dy * dy);
                if (grad_norm == 0) {
                    grad_norm = 1; // 勾配がゼロの場合は、1 で除算を防ぐ
                }
                double div = (dx / grad_norm) + (dy / grad_norm);
                temp[y * w + x] = in[y * w + x] + lambda * (in[y * w + x] - out[y * w + x]) - div;
            }
        }

        // 辺のピクセルの処理
        for (int y = 0; y < h; y++) {
            temp[y * w] = in[y * w];
            temp[y * w + w - 1] = in[y * w + w - 1];
        }
        for (int x = 0; x < w; x++) {
            temp[x] = in[x];
            temp[(h - 1) * w + x] = in[(h - 1) * w + x];
        }

        // 出力画像を更新
        for (int i = 0; i < h * w; i++) {
            out[i] = temp[i];
        }

        // 一時配列を解放
        free(temp);
    }
}
