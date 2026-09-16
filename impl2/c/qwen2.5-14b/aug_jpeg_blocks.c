#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の高さと幅が 8 の倍数でない場合、エッジをリピートしてパディングする
    int padded_h = (h + 7) & ~7;
    int padded_w = (w + 7) & ~7;
    double* padded_in = (double*)malloc(padded_h * padded_w * sizeof(double));
    if (padded_in == NULL) {
        return; // メモリ確保失敗
    }

    // 入力画像をパディング
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            padded_in[y * padded_w + x] = in[y * w + x];
        }
    }

    // パディングされた画像のエッジをリピート
    for (int y = h; y < padded_h; ++y) {
        for (int x = 0; x < w; ++x) {
            padded_in[y * padded_w + x] = padded_in[(y - h) * padded_w + x];
        }
    }
    for (int y = 0; y < padded_h; ++y) {
        for (int x = w; x < padded_w; ++x) {
            padded_in[y * padded_w + x] = padded_in[y * padded_w + (x - w)];
        }
    }

    // 8x8 ブロックごとに処理
    for (int y = 0; y < padded_h; y += 8) {
        for (int x = 0; x < padded_w; x += 8) {
            double dct[8][8];
            double quant[8][8];
            double idct[8][8];

            // DCT-II 変換
            for (int i = 0; i < 8; ++i) {
                for (int j = 0; j < 8; ++j) {
                    dct[i][j] = 0.0;
                    for (int u = 0; u < 8; ++u) {
                        for (int v = 0; v < 8; ++v) {
                            int yi = (y + i + 7 * b) % padded_h;
                            int xi = (x + j + 7 * b) % padded_w;
                            double c = (i == 0) ? sqrt(1.0 / 8.0) : 1.0;
                            double s = (j == 0) ? sqrt(1.0 / 8.0) : 1.0;
                            dct[i][j] += c * s * padded_in[yi * padded_w + xi] * cos(((2 * u + 1) * i * M_PI) / 16) * cos(((2 * v + 1) * j * M_PI) / 16);
                        }
                    }
                }
            }

            // 量化
            for (int i = 0; i < 8; ++i) {
                for (int j = 0; j < 8; ++j) {
                    quant[i][j] = round(dct[i][j] * (1 + 40 * a) / 16);
                }
            }

            // 逆 DCT
            for (int i = 0; i < 8; ++i) {
                for (int j = 0; j < 8; ++j) {
                    idct[i][j] = 0.0;
                    for (int u = 0; u < 8; ++u) {
                        for (int v = 0; v < 8; ++v) {
                            double c = (u == 0) ? sqrt(1.0 / 8.0) : 1.0;
                            double s = (v == 0) ? sqrt(1.0 / 8.0) : 1.0;
                            idct[i][j] += c * s * quant[u][v] * cos(((2 * i + 1) * u * M_PI) / 16) * cos(((2 * j + 1) * v * M_PI) / 16);
                        }
                    }
                }
            }

            // 出力画像に結果を書き込む
            for (int i = 0; i < 8; ++i) {
                for (int j = 0; j < 8; ++j) {
                    int yi = y + i;
                    int xi = x + j;
                    if (yi < h && xi < w) {
                        out[yi * w + xi] = idct[i][j] / 255.0;
                    }
                }
            }
        }
    }

    // パディングされた画像のメモリを解放
    free(padded_in);
}
