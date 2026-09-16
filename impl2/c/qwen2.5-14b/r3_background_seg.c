#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 二値画像の領域を表すため、入力画像は 0.0 または 1.0 のみを想定
    // 出力画像も 0.0 または 1.0 のみを設定する

    // ラベル付け用の配列
    int *labels = (int *)malloc(h * w * sizeof(int));
    if (labels == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // ラベル付け
    int label = 1;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] == 1.0) {
                // 上の画素
                int up_label = (y > 0 && in[(y - 1) * w + x] == 1.0) ? labels[(y - 1) * w + x] : 0;
                // 左の画素
                int left_label = (x > 0 && in[y * w + x - 1] == 1.0) ? labels[y * w + x - 1] : 0;

                if (up_label == 0 && left_label == 0) {
                    labels[y * w + x] = label++;
                } else if (up_label == 0) {
                    labels[y * w + x] = left_label;
                } else if (left_label == 0) {
                    labels[y * w + x] = up_label;
                } else {
                    labels[y * w + x] = up_label;
                    // ラベルの統合
                    for (int i = 0; i < h * w; i++) {
                        if (labels[i] == left_label) {
                            labels[i] = up_label;
                        }
                    }
                }
            } else {
                labels[y * w + x] = 0;
            }
        }
    }

    // 各ラベルの面積を計算
    int *label_areas = (int *)calloc(label, sizeof(int));
    if (label_areas == NULL) {
        free(labels);
        return;
    }

    for (int i = 0; i < h * w; i++) {
        label_areas[labels[i]]++;
    }

    // 最大ラベルの面積を計算
    int max_area = 0;
    for (int i = 1; i < label; i++) {
        if (label_areas[i] > max_area) {
            max_area = label_areas[i];
        }
    }

    // 面積のしきい値を計算
    int threshold_area = (int)(max_area * a);

    // 出力画像を設定
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (labels[y * w + x] == 0) {
                out[y * w + x] = 0.0;
            } else if (label_areas[labels[y * w + x]] >= threshold_area) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }

    // メモリ解放
    free(labels);
    free(label_areas);
}
