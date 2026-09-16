#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 円盤の半径を計算
    int radius = 1 + (int)(a * 3);
    int disk_size = 2 * radius + 1;

    // 円盤の footprint を作成
    int* footprint = (int*)malloc(disk_size * disk_size * sizeof(int));
    for (int y = -radius; y <= radius; y++) {
        for (int x = -radius; x <= radius; x++) {
            if (sqrt(x * x + y * y) <= radius) {
                footprint[(y + radius) * disk_size + (x + radius)] = 1;
            } else {
                footprint[(y + radius) * disk_size + (x + radius)] = 0;
            }
        }
    }

    // 出力画像を初期化
    memset(out, 0, h * w * sizeof(double));

    // 各画素に対してメディアンフィルタリングを適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double values[disk_size * disk_size];
            int count = 0;

            // 円盤の footprint 内の画素を取得
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        values[count++] = in[ny * w + nx];
                    } else {
                        // 端の画素は最近傍の画素を複製する
                        int ny_wrap = (ny < 0) ? 0 : (ny >= h ? h - 1 : ny);
                        int nx_wrap = (nx < 0) ? 0 : (nx >= w ? w - 1 : nx);
                        values[count++] = in[ny_wrap * w + nx_wrap];
                    }
                }
            }

            // 取得した画素の値をソート
            qsort(values, count, sizeof(double), (int (*)(const void *, const void *))compare);

            // メディアン値を出力画像に設定
            out[y * w + x] = values[count / 2];
        }
    }

    // メモリを解放
    free(footprint);
}

// 比較関数
int compare(const void *a, const void *b) {
    return (*(double*)a > *(double*)b) - (*(double*)a < *(double*)b);
}
