#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。この関数では無視する。
    // 凸包を計算するための配列を確保する。
    int* x = (int*)malloc(h * w * sizeof(int));
    int* y = (int*)malloc(h * w * sizeof(int));
    int* hull = (int*)malloc(h * w * sizeof(int));
    int num_points = 0;

    // 入力画像から点のリストを生成
    for (int y_idx = 0; y_idx < h; y_idx++) {
        for (int x_idx = 0; x_idx < w; x_idx++) {
            if (in[y_idx * w + x_idx] == 1.0) {
                x[num_points] = x_idx;
                y[num_points] = y_idx;
                num_points++;
            }
        }
    }

    // Graham Scan 法で凸包を計算
    int hull_size = 0;
    for (int i = 0; i < num_points; i++) {
        while (hull_size >= 2 && orientation(hull[hull_size - 2], hull[hull_size - 1], i) <= 0) {
            hull_size--;
        }
        hull[hull_size++] = i;
    }
    for (int i = num_points - 1, t = hull_size; i >= 0; i--) {
        while (hull_size > t && orientation(hull[hull_size - 2], hull[hull_size - 1], i) <= 0) {
            hull_size--;
        }
        hull[hull_size++] = i;
    }

    // 凸包を塗りつぶす
    for (int i = 0; i < hull_size; i++) {
        int x1 = x[hull[i]], y1 = y[hull[i]];
        int x2 = x[hull[(i + 1) % hull_size]], y2 = y[hull[(i + 1) % hull_size]];
        int dx = x2 - x1, dy = y2 - y1;
        int d = abs(dx) + abs(dy);
        int sx = dx > 0 ? 1 : -1;
        int sy = dy > 0 ? 1 : -1;
        int err = (dx > 0 ? dx : -dx) - (dy > 0 ? dy : -dy) / 2;

        for (int k = 0; k <= d; k++) {
            int xk = x1 + k * sx;
            int yk = y1 + k * sy;
            if (xk >= 0 && xk < w && yk >= 0 && yk < h) {
                out[yk * w + xk] = 1.0;
            }
            err += (dx > 0 ? dx : -dx) - (dy > 0 ? dy : -dy);
            if (err > 0) {
                xk += sx;
                yk += sy;
                err -= d;
            }
        }
    }

    // 配列を解放
    free(x);
    free(y);
    free(hull);
}

// 3点 (x1, y1), (x2, y2), (x3, y3) の進行方向を判定
int orientation(int x1, int y1, int x2, int y2, int x3, int y3) {
    return (x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1);
}
