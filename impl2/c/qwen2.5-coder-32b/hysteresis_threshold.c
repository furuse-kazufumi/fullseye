#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    double low_threshold = 0.2 + 0.3 * a;
    double high_threshold = 0.5 + 0.3 * b;

    // Initialize output to 0
    memset(out, 0, h * w * sizeof(double));

    // Helper function to check if a pixel is within bounds
    int is_within_bounds(int y, int x) {
        return y >= 0 && y < h && x >= 0 && x < w;
    }

    // Helper function to perform DFS for connected components
    void dfs(int y, int x) {
        if (!is_within_bounds(y, x) || out[y * w + x] == 1.0) {
            return;
        }
        if (in[y * w + x] >= low_threshold) {
            out[y * w + x] = 1.0;
            // Explore 8 neighbors
            dfs(y - 1, x - 1);
            dfs(y - 1, x);
            dfs(y - 1, x + 1);
            dfs(y, x - 1);
            dfs(y, x + 1);
            dfs(y + 1, x - 1);
            dfs(y + 1, x);
            dfs(y + 1, x + 1);
        }
    }

    // First pass: Identify pixels above high threshold
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] >= high_threshold) {
                out[y * w + x] = 1.0;
            }
        }
    }

    // Second pass: Use DFS to connect pixels above low threshold to high threshold pixels
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (out[y * w + x] == 1.0) {
                dfs(y, x);
            }
        }
    }
}
