#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // N = 2 + int(a * 4), clamp a to [0, 1]
    int N = 2 + (int)(a * 4);
    if (N < 2) N = 2;
    if (N > 6) N = 6;

    // Determine the bounding box of the input region
    int top = h, bottom = 0, left = w, right = 0;
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (in[y * w + x] > 0.5) {
                if (y < top) top = y;
                if (y > bottom) bottom = y;
                if (x < left) left = x;
                if (x > right) right = x;
            }
        }
    }

    // If the bounding box is smaller than the grid, adjust N
    if (bottom - top + 1 < N) N = bottom - top + 1;
    if (right - left + 1 < N) N = right - left + 1;

    // Create the grid
    int grid_h = (bottom - top + 1) / N;
    int grid_w = (right - left + 1) / N;
    int grid_top = top, grid_bottom = top + grid_h * N - 1;
    int grid_left = left, grid_right = left + grid_w * N - 1;

    // Initialize output to zero
    memset(out, 0, h * w * sizeof(double));

    // Fill the output with 1.0 for cells overlapping the region
    for (int y = grid_top; y <= grid_bottom; y += grid_h) {
        for (int x = grid_left; x <= grid_right; x += grid_w) {
            int cell_top = y, cell_bottom = y + grid_h - 1;
            int cell_left = x, cell_right = x + grid_w - 1;

            // Skip cells that do not overlap the region
            if (cell_top > bottom || cell_bottom < top || cell_left > right || cell_right < left) continue;

            // Mark the cell as overlapping the region
            for (int cy = cell_top; cy <= cell_bottom; ++cy) {
                for (int cx = cell_left; cx <= cell_right; ++cx) {
                    if (cy >= 0 && cy < h && cx >= 0 && cx < w) {
                        out[cy * w + cx] = 1.0;
                    }
                }
            }
        }
    }
}
