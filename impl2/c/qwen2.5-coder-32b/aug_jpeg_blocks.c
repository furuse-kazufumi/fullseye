#include <math.h>
#include <stdlib.h>
#include <string.h>

#define BLOCK_SIZE 8

// 辺の長さが BLOCK_SIZE の倍数でない場合の境界処理方法:
// エッジレプリケーションパディングを使用する。

// 8x8 DCT-II 実装
void dct2(double* block) {
    double temp[BLOCK_SIZE][BLOCK_SIZE];
    double c1 = 1.0 / sqrt(2.0);
    double c2 = 1.0;

    // 行方向の DCT-II
    for (int y = 0; y < BLOCK_SIZE; y++) {
        for (int x = 0; x < BLOCK_SIZE; x++) {
            double sum = 0.0;
            for (int u = 0; u < BLOCK_SIZE; u++) {
                sum += block[y * BLOCK_SIZE + u] * cos((M_PI * (2 * x + 1) * u) / (2 * BLOCK_SIZE));
            }
            temp[y][x] = sum * (x == 0 ? c1 : c2);
        }
    }

    // 列方向の DCT-II
    for (int x = 0; x < BLOCK_SIZE; x++) {
        for (int y = 0; y < BLOCK_SIZE; y++) {
            double sum = 0.0;
            for (int v = 0; v < BLOCK_SIZE; v++) {
                sum += temp[v][x] * cos((M_PI * (2 * y + 1) * v) / (2 * BLOCK_SIZE));
            }
            block[y * BLOCK_SIZE + x] = sum * (y == 0 ? c1 : c2);
        }
    }
}

// 8x8 逆 DCT-II 実装
void idct2(double* block) {
    double temp[BLOCK_SIZE][BLOCK_SIZE];
    double c1 = 1.0 / sqrt(2.0);
    double c2 = 1.0 / 2.0;

    // 行方向の逆 DCT-II
    for (int y = 0; y < BLOCK_SIZE; y++) {
        for (int x = 0; x < BLOCK_SIZE; x++) {
            double sum = 0.0;
            for (int u = 0; u < BLOCK_SIZE; u++) {
                sum += (u == 0 ? c1 : c2) * block[u * BLOCK_SIZE + x] * cos((M_PI * u * (2 * y + 1)) / (2 * BLOCK_SIZE));
            }
            temp[y][x] = sum;
        }
    }

    // 列方向の逆 DCT-II
    for (int x = 0; x < BLOCK_SIZE; x++) {
        for (int y = 0; y < BLOCK_SIZE; y++) {
            double sum = 0.0;
            for (int v = 0; v < BLOCK_SIZE; v++) {
                sum += (v == 0 ? c1 : c2) * temp[y][v] * cos((M_PI * v * (2 * x + 1)) / (2 * BLOCK_SIZE));
            }
            block[y * BLOCK_SIZE + x] = sum;
        }
    }
}

// JPEG 標準 Annex-K ライュナンス量子化テーブル
const int jpeg_quant_table[BLOCK_SIZE][BLOCK_SIZE] = {
    {16, 11, 10, 16, 24, 40, 51, 61},
    {12, 12, 14, 19, 26, 58, 60, 55},
    {14, 13, 16, 24, 40, 57, 69, 56},
    {14, 17, 22, 29, 51, 87, 80, 62},
    {18, 22, 37, 56, 68, 109, 103, 77},
    {24, 35, 55, 64, 81, 104, 113, 92},
    {49, 64, 78, 87, 103, 121, 120, 101},
    {72, 92, 95, 98, 112, 100, 103, 99}
};

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // パディングサイズ計算
    int padded_h = (h + BLOCK_SIZE - 1) / BLOCK_SIZE * BLOCK_SIZE;
    int padded_w = (w + BLOCK_SIZE - 1) / BLOCK_SIZE * BLOCK_SIZE;
    int pad_h = padded_h - h;
    int pad_w = padded_w - w;

    // パディングされた画像のメモリ確保
    double* padded_in = (double*)malloc(padded_h * padded_w * sizeof(double));
    if (!padded_in) return;

    // エッジレプリケーションパディング
    for (int y = 0; y < padded_h; y++) {
        for (int x = 0; x < padded_w; x++) {
            int src_y = y < h ? y : h - 1;
            int src_x = x < w ? x : w - 1;
            padded_in[y * padded_w + x] = in[src_y * w + src_x];
        }
    }

    // 量子化スケールファクタ計算
    double scale = (1.0 + 40.0 * a) / 16.0;

    // ブロックシフト計算
    int block_shift = (int)(7.0 * b);

    // 処理用一時領域確保
    double* block = (double*)malloc(BLOCK_SIZE * BLOCK_SIZE * sizeof(double));
    if (!block) {
        free(padded_in);
        return;
    }

    // ブロックごとに DCT, 量子化, 逆 DCT を行う
    for (int by = 0; by < padded_h; by += BLOCK_SIZE) {
        for (int bx = 0; bx < padded_w; bx += BLOCK_SIZE) {
            // ブロックの読み込み
            for (int y = 0; y < BLOCK_SIZE; y++) {
                for (int x = 0; x < BLOCK_SIZE; x++) {
                    int src_y = (by + y - block_shift + padded_h) % padded_h;
                    int src_x = (bx + x - block_shift + padded_w) % padded_w;
                    block[y * BLOCK_SIZE + x] = padded_in[src_y * padded_w + src_x] * 255.0;
                }
            }

            // DCT-II
            dct2(block);

            // 量子化
            for (int y = 0; y < BLOCK_SIZE; y++) {
                for (int x = 0; x < BLOCK_SIZE; x++) {
                    block[y * BLOCK_SIZE + x] = round(block[y * BLOCK_SIZE + x] / (jpeg_quant_table[y][x] * scale));
                }
            }

            // 逆量子化
            for (int y = 0; y < BLOCK_SIZE; y++) {
                for (int x = 0; x < BLOCK_SIZE; x++) {
                    block[y * BLOCK_SIZE + x] *= jpeg_quant_table[y][x] * scale;
                }
            }

            // 逆 DCT-II
            idct2(block);

            // ブロックの書き込み
            for (int y = 0; y < BLOCK_SIZE; y++) {
                for (int x = 0; x < BLOCK_SIZE; x++) {
                    int dst_y = by + y;
                    int dst_x = bx + x;
                    if (dst_y < h && dst_x < w) {
                        out[dst_y * w + dst_x] = fmin(fmax(block[y * BLOCK_SIZE + x] / 255.0, 0.0), 1.0);
                    }
                }
            }
        }
    }

    // メモリ解放
    free(padded_in);
    free(block);
}
