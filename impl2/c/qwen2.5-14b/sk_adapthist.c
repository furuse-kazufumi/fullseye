#include <math.h>
#include <stdlib.h>
#include <string.h>

#define TILE_SIZE 8
#define CLIP_LIMIT 0.01

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は CLIP_LIMIT を調整するパラメータとして使用しますが、仕様書では b は使用されないと明記されています。
    // CLIP_LIMIT の計算
    double clip_limit = CLIP_LIMIT + 0.05 * a;

    // 各タイルのヒストグラムを保持する配列
    double tile_histograms[TILE_SIZE * TILE_SIZE][256];
    memset(tile_histograms, 0, sizeof(tile_histograms));

    // 各タイルの最大ヒストグラム値を保持する配列
    double tile_max_histograms[TILE_SIZE * TILE_SIZE];
    memset(tile_max_histograms, 0, sizeof(tile_max_histograms));

    // 各タイルの累積ヒストグラムを保持する配列
    double tile_cumulative_histograms[TILE_SIZE * TILE_SIZE][256];
    memset(tile_cumulative_histograms, 0, sizeof(tile_cumulative_histograms));

    // 各タイルの累積ヒストグラムを計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int tile_y = y / TILE_SIZE;
            int tile_x = x / TILE_SIZE;
            int tile_index = tile_y * TILE_SIZE + tile_x;
            int pixel_value = (int)(in[y * w + x] * 255.0);

            tile_histograms[tile_index][pixel_value]++;
            tile_max_histograms[tile_index] = fmax(tile_max_histograms[tile_index], tile_histograms[tile_index][pixel_value]);
        }
    }

    // 各タイルの累積ヒストグラムを計算
    for (int tile_index = 0; tile_index < TILE_SIZE * TILE_SIZE; tile_index++) {
        double cumulative_sum = 0.0;
        for (int i = 0; i < 256; i++) {
            cumulative_sum += tile_histograms[tile_index][i];
            tile_cumulative_histograms[tile_index][i] = cumulative_sum;
        }
    }

    // 各タイルの累積ヒストグラムを CLIP_LIMIT でクリッピング
    for (int tile_index = 0; tile_index < TILE_SIZE * TILE_SIZE; tile_index++) {
        double clip_value = clip_limit * tile_max_histograms[tile_index];
        for (int i = 0; i < 256; i++) {
            if (tile_cumulative_histograms[tile_index][i] > clip_value) {
                tile_cumulative_histograms[tile_index][i] = clip_value;
            }
        }
    }

    // 各タイルの累積ヒストグラムを正規化
    for (int tile_index = 0; tile_index < TILE_SIZE * TILE_SIZE; tile_index++) {
        double max_value = tile_cumulative_histograms[tile_index][255];
        for (int i = 0; i < 256; i++) {
            tile_cumulative_histograms[tile_index][i] = tile_cumulative_histograms[tile_index][i] / max_value * 255.0;
        }
    }

    // 出力画像を生成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int tile_y = y / TILE_SIZE;
            int tile_x = x / TILE_SIZE;
            int tile_index = tile_y * TILE_SIZE + tile_x;
            int pixel_value = (int)(in[y * w + x] * 255.0);

            int mapped_value = (int)(tile_cumulative_histograms[tile_index][pixel_value]);
            out[y * w + x] = mapped_value / 255.0;
        }
    }
}
