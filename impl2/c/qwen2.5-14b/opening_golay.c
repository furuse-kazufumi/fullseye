#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 圆形结构元素的半径
    int radius = (int)(a * 4); // 假设半径范围为1到4，这里使用a参数进行缩放
    if (radius < 1) radius = 1; // 确保半径至少为1
    if (radius > 4) radius = 4; // 确保半径不超过4

    // 边缘填充，假设边缘填充为背景（0）
    int padded_h = h + 2 * radius;
    int padded_w = w + 2 * radius;
    double* padded_in = (double*)malloc(padded_h * padded_w * sizeof(double));
    memset(padded_in, 0, padded_h * padded_w * sizeof(double));

    // 填充原始图像到边缘填充的图像中
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            padded_in[(y + radius) * padded_w + (x + radius)] = in[y * w + x];
        }
    }

    // 执行腐蚀操作
    double* eroded = (double*)malloc(padded_h * padded_w * sizeof(double));
    memset(eroded, 0, padded_h * padded_w * sizeof(double));
    for (int y = radius; y < padded_h - radius; y++) {
        for (int x = radius; x < padded_w - radius; x++) {
            double max_dist = radius * sqrt(2); // 圆形结构元素的最大距离
            double sum = 0;
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    double dist = sqrt(dx * dx + dy * dy);
                    if (dist <= max_dist) {
                        sum += padded_in[(y + dy) * padded_w + (x + dx)];
                    }
                }
            }
            eroded[y * padded_w + x] = (sum > 0) ? 1 : 0;
        }
    }

    // 执行膨胀操作
    memset(out, 0, h * w * sizeof(double));
    for (int y = radius; y < padded_h - radius; y++) {
        for (int x = radius; x < padded_w - radius; x++) {
            double sum = 0;
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    double dist = sqrt(dx * dx + dy * dy);
                    if (dist <= max_dist) {
                        sum += eroded[(y + dy) * padded_w + (x + dx)];
                    }
                }
            }
            out[(y - radius) * w + (x - radius)] = (sum > 0) ? 1 : 0;
        }
    }

    // 释放内存
    free(padded_in);
    free(eroded);
}
