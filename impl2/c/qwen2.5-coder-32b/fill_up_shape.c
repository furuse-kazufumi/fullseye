#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は使用しない
    int area_threshold = 16 + 200 * a;
    int* label = (int*)calloc(h * w, sizeof(int));
    int* size = (int*)calloc(h * w, sizeof(int));
    int label_count = 0;

    // ラベリング
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] > 0.5) {
                int current_label = 0;
                int neighbors[4] = {0};
                int neighbor_count = 0;

                if (x > 0 && label[y * w + x - 1] > 0) {
                    neighbors[neighbor_count++] = label[y * w + x - 1];
                }
                if (y > 0 && label[(y - 1) * w + x] > 0) {
                    neighbors[neighbor_count++] = label[(y - 1) * w + x];
                }

                if (neighbor_count == 0) {
                    current_label = ++label_count;
                } else {
                    current_label = neighbors[0];
                    for (int i = 1; i < neighbor_count; i++) {
                        if (neighbors[i] < current_label) {
                            current_label = neighbors[i];
                        }
                    }
                    for (int i = 0; i < neighbor_count; i++) {
                        if (neighbors[i] != current_label) {
                            for (int j = 1; j <= label_count; j++) {
                                if (label[j] == neighbors[i]) {
                                    label[j] = current_label;
                                }
                            }
                        }
                    }
                }
                label[y * w + x] = current_label;
                size[current_label]++;
            }
        }
    }

    // ラベルのマージ
    for (int i = 1; i <= label_count; i++) {
        if (label[i] != i) {
            size[label[i]] += size[i];
            size[i] = 0;
        }
    }

    // 出力生成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int current_label = label[y * w + x];
            if (current_label > 0 && size[current_label] > area_threshold) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }

    free(label);
    free(size);
}
