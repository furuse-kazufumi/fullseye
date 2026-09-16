#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 圆形结构元素的半径计算
    int radius = (int)round(_rad(a) * 4); // _rad(a) 为 0 到 1 的值，这里假设 _rad(a) 为线性映射到 0 到 4 的范围
    if (radius < 1) radius = 1; // 半径至少为 1

    // 初始化输出数组
    memset(out, 0, h * w * sizeof(double));

    // 定义一个函数来检查给定点是否在圆内
    int is_in_circle(int x, int y, int center_x, int center_y, int radius) {
        return (x - center_x) * (x - center_x) + (y - center_y) * (y - center_y) <= radius * radius;
    }

    // 对每个像素进行处理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] == 1.0) { // 如果当前像素是前景
                int count = 0;
                for (int dy = -radius; dy <= radius; dy++) {
                    for (int dx = -radius; dx <= radius; dx++) {
                        int nx = x + dx;
                        int ny = y + dy;
                        // 检查边界条件
                        if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                            if (is_in_circle(nx, ny, x, y, radius) && in[ny * w + nx] == 1.0) {
                                count++;
                            }
                        }
                    }
                }
                // 如果圆内的所有像素都是前景，则输出为前景
                if (count == (2 * radius + 1) * (2 * radius + 1)) {
                    out[y * w + x] = 1.0;
                }
            }
        }
    }
}

// 假设的 _rad 函数，这里直接返回 a，实际使用时需要替换为正确的映射函数
double _rad(double a) {
    return a;
}
