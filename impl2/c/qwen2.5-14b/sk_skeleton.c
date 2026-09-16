#include <math.h>
#include <stdlib.h>
#include <string.h>

// Helper function to check if a pixel is on the border of the image
static inline int is_border(int y, int x, int h, int w) {
    return y == 0 || x == 0 || y == h - 1 || x == w - 1;
}

// Helper function to get the value of a pixel, considering border conditions
static inline int get_pixel(const double* in, int y, int x, int h, int w) {
    if (y < 0 || y >= h || x < 0 || x >= w) {
        return 0; // Treat border pixels as background (0)
    }
    return in[y * w + x] > 0.5;
}

// Helper function to count the number of live neighbors for a given pixel
static int count_live_neighbors(const double* in, int y, int x, int h, int w) {
    int count = 0;
    for (int dy = -1; dy <= 1; ++dy) {
        for (int dx = -1; dx <= 1; ++dx) {
            if (dy == 0 && dx == 0) continue;
            count += get_pixel(in, y + dy, x + dx, h, w);
        }
    }
    return count;
}

// Helper function to count the number of live diagonal neighbors for a given pixel
static int count_live_diagonal_neighbors(const double* in, int y, int x, int h, int w) {
    int count = 0;
    for (int dy = -1; dy <= 1; ++dy) {
        for (int dx = -1; dx <= 1; ++dx) {
            if (abs(dy) == abs(dx)) {
                count += get_pixel(in, y + dy, x + dx, h, w);
            }
        }
    }
    return count;
}

// Helper function to check if a pixel can be removed in the Zhang-Suen thinning process
static int can_remove_pixel(const double* in, int y, int x, int h, int w) {
    int live_neighbors = count_live_neighbors(in, y, x, h, w);
    int live_diagonal_neighbors = count_live_diagonal_neighbors(in, y, x, h, w);
    int p2 = get_pixel(in, y, x - 1, h, w);
    int p3 = get_pixel(in, y - 1, x - 1, h, w);
    int p4 = get_pixel(in, y - 1, x, h, w);
    int p5 = get_pixel(in, y - 1, x + 1, h, w);
    int p6 = get_pixel(in, y, x + 1, h, w);
    int p7 = get_pixel(in, y + 1, x + 1, h, w);
    int p8 = get_pixel(in, y + 1, x, h, w);
    int p9 = get_pixel(in, y + 1, x - 1, h, w);

    int a1 = (p2 && !p3 && !p4) || (!p2 && p3 && !p4) || (!p2 && !p3 && p4);
    int a2 = (p4 && !p5 && !p6) || (!p4 && p5 && !p6) || (!p4 && !p5 && p6);
    int a3 = (p6 && !p7 && !p8) || (!p6 && p7 && !p8) || (!p6 && !p7 && p8);
    int a4 = (p8 && !p9 && !p2) || (!p8 && p9 && !p2) || (!p8 && !p9 && p2);

    return live_neighbors == 2 && (a1 || a2 || a3 || a4) && live_diagonal_neighbors < 2;
}

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // First pass of Zhang-Suen thinning
    int* temp = (int*)malloc(h * w * sizeof(int));
    memcpy(temp, in, h * w * sizeof(double));
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            if (can_remove_pixel(temp, y, x, h, w)) {
                temp[y * w + x] = 0;
            }
        }
    }

    // Second pass of Zhang-Suen thinning
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            if (can_remove_pixel(temp, y, x, h, w)) {
                temp[y * w + x] = 0;
            }
        }
    }

    // Copy the result back to the output array
    for (int i = 0; i < h * w; ++i) {
        out[i] = temp[i] > 0.5 ? 1.0 : 0.0;
    }

    free(temp);
}
