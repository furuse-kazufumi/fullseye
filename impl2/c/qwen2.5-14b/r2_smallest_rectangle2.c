#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // この実装では、入力画像が二値画像であると仮定します。
    // 1.0 は領域に属する画素を表し、0.0 は背景を表します。

    // 凸包の座標を格納する配列
    int convex_hull[h * w][2];
    int convex_hull_size = 0;

    // 凸包の座標を取得
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] > 0.5) {
                convex_hull[convex_hull_size][0] = x;
                convex_hull[convex_hull_size][1] = y;
                convex_hull_size++;
            }
        }
    }

    // 凸包の座標を格納する配列を確保
    double* convex_hull_sorted = (double*)malloc(convex_hull_size * 2 * sizeof(double));
    if (convex_hull_sorted == NULL) {
        exit(EXIT_FAILURE);
    }

    // 凸包の座標をソート
    for (int i = 0; i < convex_hull_size; i++) {
        convex_hull_sorted[2 * i] = convex_hull[i][0];
        convex_hull_sorted[2 * i + 1] = convex_hull[i][1];
    }

    // 凸包の座標をソート
    qsort(convex_hull_sorted, convex_hull_size, 2 * sizeof(double), compare);

    // 最小外接矩形の計算
    double min_area = INFINITY;
    double cx, cy, long_len, short_len, angle;
    for (int i = 0; i < convex_hull_size; i++) {
        double dx1 = convex_hull_sorted[2 * i] - convex_hull_sorted[2 * (i + 1) % convex_hull_size];
        double dy1 = convex_hull_sorted[2 * i + 1] - convex_hull_sorted[2 * (i + 1) % convex_hull_size];
        double dx2 = convex_hull_sorted[2 * (i + 1) % convex_hull_size] - convex_hull_sorted[2 * (i + 2) % convex_hull_size];
        double dy2 = convex_hull_sorted[2 * (i + 1) % convex_hull_size] - convex_hull_sorted[2 * (i + 2) % convex_hull_size];
        double angle1 = atan2(dy1, dx1);
        double angle2 = atan2(dy2, dx2);
        double angle_diff = angle2 - angle1;
        if (angle_diff < 0) {
            angle_diff += 2 * M_PI;
        }
        double cos_angle_diff = cos(angle_diff);
        double sin_angle_diff = sin(angle_diff);
        double long_len_squared = dx1 * dx1 + dy1 * dy1;
        double short_len_squared = dx2 * dx2 + dy2 * dy2;
        double area = sqrt(long_len_squared * short_len_squared * cos_angle_diff * cos_angle_diff + long_len_squared * short_len_squared * sin_angle_diff * sin_angle_diff);
        if (area < min_area) {
            min_area = area;
            cx = (convex_hull_sorted[2 * i] + convex_hull_sorted[2 * (i + 1) % convex_hull_size]) / 2;
            cy = (convex_hull_sorted[2 * i + 1] + convex_hull_sorted[2 * (i + 1) % convex_hull_size]) / 2;
            long_len = sqrt(long_len_squared);
            short_len = sqrt(short_len_squared);
            angle = angle1;
        }
    }

    // 最小外接矩形を描画
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double dx = x - cx;
            double dy = y - cy;
            double cos_angle = cos(angle);
            double sin_angle = sin(angle);
            double px = dx * cos_angle - dy * sin_angle;
            double py = dx * sin_angle + dy * cos_angle;
            if (fabs(px) <= long_len / 2 + 0.5 && fabs(py) <= short_len / 2 + 0.5) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }

    // メモリを解放
    free(convex_hull_sorted);
}

// 比較関数
int compare(const void* a, const void* b) {
    double* pa = (double*)a;
    double* pb = (double*)b;
    if (pa[0] < pb[0]) return -1;
    if (pa[0] > pb[0]) return 1;
    if (pa[1] < pb[1]) return -1;
    if (pa[1] > pb[1]) return 1;
    return 0;
}
