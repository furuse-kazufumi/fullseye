#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // CLAHE の実装では、入力画像を 8x8 のタイルに分割し、各タイルに対してヒストグラム均等化を適用します。
    // ここでは、簡単のため、タイルサイズを 8x8 と固定します。
    const int tile_size = 8;
    const int clip_limit = 1.0 + 4.0 * a; // コントラスト制限の強さ

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 各タイルに対して CLAHE を適用
    for (int ty = 0; ty < h; ty += tile_size) {
        for (int tx = 0; tx < w; tx += tile_size) {
            // タイルの範囲を計算
            int tile_h = (ty + tile_size < h) ? tile_size : (h - ty);
            int tile_w = (tx + tile_size < w) ? tile_size : (w - tx);

            // タイル内のヒストグラムを計算
            int hist[256] = {0};
            for (int y = 0; y < tile_h; y++) {
                for (int x = 0; x < tile_w; x++) {
                    int idx = (int)(in[(ty + y) * w + (tx + x)] * 255.0);
                    hist[idx]++;
                }
            }

            // クリッピングされたヒストグラムを計算
            int clip_hist[256] = {0};
            int clip_count = 0;
            for (int i = 0; i < 256; i++) {
                clip_hist[i] = clip_limit * hist[i];
                clip_count += clip_hist[i];
            }

            // クリッピングされたヒストグラムの累積分布関数 (CDF) を計算
            int cdf[256] = {0};
            int cdf_sum = 0;
            for (int i = 0; i < 256; i++) {
                cdf_sum += clip_hist[i];
                cdf[i] = cdf_sum;
            }

            // CDF を 255 で割って正規化
            for (int i = 0; i < 256; i++) {
                cdf[i] = (cdf[i] * 255) / cdf[255];
            }

            // タイル内のピクセルに対して CLAHE を適用
            for (int y = 0; y < tile_h; y++) {
                for (int x = 0; x < tile_w; x++) {
                    int idx = (int)(in[(ty + y) * w + (tx + x)] * 255.0);
                    out[(ty + y) * w + (tx + x)] = cdf[idx] / 255.0;
                }
            }
        }
    }
}
