#include <math.h>
#include <stdlib.h>
#include <string.h>

// 定数定義
#define PI 3.14159265358979323846
#define KERNEL_SIZE 3
#define NUM_KERNELS 8

// 各カーネルの定義
const double _ROBINSON[NUM_KERNELS][KERNEL_SIZE][KERNEL_SIZE] = {
    {{-1, 0, 1}, {-1, 0, 1}, {-1, 0, 1}},
    {{-1, 0, 1}, {-1, 0, 1}, {0, 1, -1}},
    {{-1, 0, 1}, {0, 1, -1}, {1, -1, -1}},
    {{0, 1, -1}, {1, -1, -1}, {1, -1, 0}},
    {{1, -1, 0}, {1, -1, -1}, {0, 1, -1}},
    {{1, -1, -1}, {0, 1, -1}, {-1, 0, 1}},
    {{1, -1, -1}, {-1, 0, 1}, {-1, 0, 1}},
    {{0, 1, -1}, {-1, 0, 1}, {-1, 0, 1}}
};

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 画像の各ピクセルに対して処理を行う
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double max_response = -INFINITY;
            int max_kernel_index = -1;

            // 8 方向のカーネルに対して畳み込みを行う
            for (int k = 0; k < NUM_KERNELS; k++) {
                double response = 0.0;

                // 畳み込みの計算
                for (int ky = 0; ky < KERNEL_SIZE; ky++) {
                    for (int kx = 0; kx < KERNEL_SIZE; kx++) {
                        response += _ROBINSON[k][ky][kx] * in[(y + ky - 1) * w + (x + kx - 1)];
                    }
                }

                // 最大応答を更新
                if (response > max_response) {
                    max_response = response;
                    max_kernel_index = k;
                }
            }

            // 最大応答のカーネル番号を正規化して出力画像に書き込む
            out[y * w + x] = max_kernel_index / (NUM_KERNELS - 1.0);
        }
    }
}
