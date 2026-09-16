#include <math.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    int x, y;
} Point;

// 比較関数: y が優先で、次に x で比較
int compare_points(const void* a, const void* b) {
    Point* pa = (Point*)a;
    Point* pb = (Point*)b;
    if (pa->y == pb->y) {
        return pa->x - pb->x;
    }
    return pa->y - pb->y;
}

// グラハム スキャン アルゴリズムを使用して凸包を計算
void convex_hull(Point* points, int n, Point** hull, int* hull_size) {
    if (n < 3) {
        *hull_size = n;
        *hull = (Point*)malloc(n * sizeof(Point));
        memcpy(*hull, points, n * sizeof(Point));
        return;
    }

    qsort(points, n, sizeof(Point), compare_points);

    Point* lower_hull = (Point*)malloc(n * sizeof(Point));
    int lower_size = 0;

    for (int i = 0; i < n; i++) {
        while (lower_size >= 2) {
            Point p0 = lower_hull[lower_size - 2];
            Point p1 = lower_hull[lower_size - 1];
            Point p2 = points[i];
            int cross_product = (p1.x - p0.x) * (p2.y - p0.y) - (p1.y - p0.y) * (p2.x - p0.x);
            if (cross_product <= 0) {
                lower_size--;
            } else {
                break;
            }
        }
        lower_hull[lower_size++] = points[i];
    }

    Point* upper_hull = (Point*)malloc(n * sizeof(Point));
    int upper_size = 0;

    for (int i = n - 1; i >= 0; i--) {
        while (upper_size >= 2) {
            Point p0 = upper_hull[upper_size - 2];
            Point p1 = upper_hull[upper_size - 1];
            Point p2 = points[i];
            int cross_product = (p1.x - p0.x) * (p2.y - p0.y) - (p1.y - p0.y) * (p2.x - p0.x);
            if (cross_product <= 0) {
                upper_size--;
            } else {
                break;
            }
        }
        upper_hull[upper_size++] = points[i];
    }

    *hull_size = lower_size + upper_size - 2;
    *hull = (Point*)malloc(*hull_size * sizeof(Point));
    memcpy(*hull, lower_hull, lower_size * sizeof(Point));
    memcpy(*hull + lower_size, upper_hull + 1, (upper_size - 1) * sizeof(Point));

    free(lower_hull);
    free(upper_hull);
}

void fill_convex_hull(Point* hull, int hull_size, int h, int w, double* out) {
    memset(out, 0, h * w * sizeof(double));

    for (int i = 0; i < hull_size; i++) {
        Point p1 = hull[i];
        Point p2 = hull[(i + 1) % hull_size];
        int x1 = p1.x, y1 = p1.y;
        int x2 = p2.x, y2 = p2.y;

        // Bresenham's line algorithm to draw the line
        int dx = abs(x2 - x1), sx = x1 < x2 ? 1 : -1;
        int dy = -abs(y2 - y1), sy = y1 < y2 ? 1 : -1;
        int err = dx + dy, e2;

        while (1) {
            if (x1 >= 0 && x1 < w && y1 >= 0 && y1 < h) {
                out[y1 * w + x1] = 1.0;
            }
            if (x1 == x2 && y1 == y2) break;
            e2 = 2 * err;
            if (e2 >= dy) { err += dy; x1 += sx; }
            if (e2 <= dx) { err += dx; y1 += sy; }
        }
    }

    // Fill the region inside the convex hull
    for (int y = 0; y < h; y++) {
        int inside = 0;
        for (int x = 0; x < w; x++) {
            if (out[y * w + x] == 1.0) {
                inside = !inside;
            } else if (inside) {
                out[y * w + x] = 1.0;
            }
        }
    }
}

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    Point* points = NULL;
    int n = 0;

    // Collect all points that belong to the region
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] >= 0.5) {
                points = (Point*)realloc(points, (n + 1) * sizeof(Point));
                points[n].x = x;
                points[n].y = y;
                n++;
            }
        }
    }

    if (n == 0) {
        memset(out, 0, h * w * sizeof(double));
        free(points);
        return;
    }

    Point* hull;
    int hull_size;
    convex_hull(points, n, &hull, &hull_size);

    fill_convex_hull(hull, hull_size, h, w, out);

    free(points);
    free(hull);
}
