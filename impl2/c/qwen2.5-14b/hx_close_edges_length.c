#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 二値化しきい値 a で画像を二値化
    // 3x3 の構造要素で 1 回の binary_closing を行う
    // 連結成分をラベリングし、画素数が min_len 未満の成分を落として 0/1 の float 画像を出力する
    // min_len = 2 + int(b * 20) (2 〜 22)
    // 画像の端は 0 と扱う

    // 二値化しきい値 a で画像を二値化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = (in[y * w + x] > a) ? 1.0 : 0.0;
        }
    }

    // 3x3 の構造要素で 1 回の binary_closing を行う
    // 画像の端は 0 と扱う
    int min_len = 2 + (int)(b * 20);
    int* labels = (int*)malloc(h * w * sizeof(int));
    int* label_counts = (int*)malloc((h * w + 1) * sizeof(int));
    int num_labels = 0;

    // 連結成分をラベリング
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (out[y * w + x] == 1.0) {
                int label = 0;
                for (int dy = -1; dy <= 1; ++dy) {
                    for (int dx = -1; dx <= 1; ++dx) {
                        int ny = y + dy;
                        int nx = x + dx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w && out[ny * w + nx] == 1.0) {
                            if (label == 0) {
                                label = labels[ny * w + nx];
                            } else if (labels[ny * w + nx] != 0 && labels[ny * w + nx] != label) {
                                label = 0;
                            }
                        }
                    }
                }
                if (label == 0) {
                    label = ++num_labels;
                }
                labels[y * w + x] = label;
            }
        }
    }

    // ラベルの数をカウント
    for (int i = 0; i <= h * w; ++i) {
        label_counts[i] = 0;
    }
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (labels[y * w + x] != 0) {
                label_counts[labels[y * w + x]]++;
            }
        }
    }

    // 画素数が min_len 未満の成分を落として 0/1 の float 画像を出力する
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (labels[y * w + x] != 0 && label_counts[labels[y * w + x]] >= min_len) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }

    free(labels);
    free(label_counts);
}
