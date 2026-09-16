#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の全画素数
    int num_pixels = h * w;

    // 二値画像をラベル付けするための配列
    int* labels = (int*)malloc(num_pixels * sizeof(int));
    if (labels == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // 連結成分ラベル付け
    int num_components = 0;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int index = y * w + x;
            if (in[index] > 0.5) {
                // 4 連結のラベル付け
                int label = 1;
                if (y > 0 && labels[(y - 1) * w + x] > 0) {
                    label = labels[(y - 1) * w + x];
                } else if (x > 0 && labels[y * w + x - 1] > 0) {
                    label = labels[y * w + x - 1];
                }
                labels[index] = label;
                if (label == 0) {
                    num_components++;
                    labels[index] = num_components;
                }
            } else {
                labels[index] = 0;
            }
        }
    }

    // 各ラベルの面積を計算
    int* component_sizes = (int*)malloc(num_components * sizeof(int));
    if (component_sizes == NULL) {
        free(labels);
        return;
    }
    memset(component_sizes, 0, num_components * sizeof(int));
    for (int i = 0; i < num_pixels; i++) {
        if (labels[i] > 0) {
            component_sizes[labels[i] - 1]++;
        }
    }

    // 面積の降順にソート
    int* sorted_indices = (int*)malloc(num_components * sizeof(int));
    if (sorted_indices == NULL) {
        free(component_sizes);
        free(labels);
        return;
    }
    for (int i = 0; i < num_components; i++) {
        sorted_indices[i] = i;
    }
    for (int i = 0; i < num_components - 1; i++) {
        for (int j = 0; j < num_components - i - 1; j++) {
            if (component_sizes[j] < component_sizes[j + 1]) {
                int temp = component_sizes[j];
                component_sizes[j] = component_sizes[j + 1];
                component_sizes[j + 1] = temp;
                int temp_index = sorted_indices[j];
                sorted_indices[j] = sorted_indices[j + 1];
                sorted_indices[j + 1] = temp_index;
            }
        }
    }

    // k 番目の成分を決定
    int k = (int)round(a * (num_components - 1));
    if (k < 0) k = 0;
    if (k >= num_components) k = num_components - 1;

    // 出力画像の生成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int index = y * w + x;
            if (labels[index] == sorted_indices[k] + 1) {
                out[index] = 1.0;
            } else {
                out[index] = 0.0;
            }
        }
    }

    // メモリ解放
    free(component_sizes);
    free(sorted_indices);
    free(labels);
}
