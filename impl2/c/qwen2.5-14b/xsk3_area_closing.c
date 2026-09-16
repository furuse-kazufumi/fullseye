#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 面積閾値の計算
    int area_threshold = 16 + (int)(a * 100);
    
    // 画像の周囲を 1 画素分の境界で囲む
    int padded_h = h + 2;
    int padded_w = w + 2;
    double* padded_in = (double*)malloc(padded_h * padded_w * sizeof(double));
    memset(padded_in, 0, padded_h * padded_w * sizeof(double));
    
    // 元の画像をパディングされた画像にコピー
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            padded_in[(y + 1) * padded_w + (x + 1)] = in[y * w + x];
        }
    }
    
    // 出力画像を初期化
    memset(out, 0, h * w * sizeof(double));
    
    // 面積クロージングの適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int area = 0;
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    if (padded_in[(y + dy + 1) * padded_w + (x + dx + 1)] > 0.5) {
                        area++;
                    }
                }
            }
            if (area < area_threshold) {
                out[y * w + x] = 1.0; // 窪みを埋める
            } else {
                out[y * w + x] = padded_in[(y + 1) * padded_w + (x + 1)]; // 元の値を保持
            }
        }
    }
    
    // メモリの解放
    free(padded_in);
}
