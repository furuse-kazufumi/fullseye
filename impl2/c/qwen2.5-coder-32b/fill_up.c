#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Copy the input to output initially
    memcpy(out, in, h * w * sizeof(double));

    // Define a function to check if a pixel is part of the region
    #define IS_REGION(x, y) ((x) >= 0 && (x) < w && (y) >= 0 && (y) < h && out[(y) * w + (x)] == 1.0)

    // Define a function to check if a pixel is a hole
    #define IS_HOLE(x, y) ((x) >= 0 && (x) < w && (y) >= 0 && (y) < h && out[(y) * w + (x)] == 0.0)

    // Define the 4-connectivity neighbors
    const int dx[] = {-1, 1, 0, 0};
    const int dy[] = {0, 0, -1, 1};

    // Use a flood fill algorithm to fill holes
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (IS_HOLE(x, y)) {
                // Check if this hole is connected to the boundary
                int is_boundary_connected = 0;
                for (int dir = 0; dir < 4; dir++) {
                    int nx = x + dx[dir];
                    int ny = y + dy[dir];
                    if (nx < 0 || nx >= w || ny < 0 || ny >= h) {
                        is_boundary_connected = 1;
                        break;
                    }
                }

                if (!is_boundary_connected) {
                    // Perform flood fill to fill this hole
                    int stack[1024]; // Assuming the maximum hole size is manageable within this stack size
                    int stack_top = 0;
                    stack[stack_top++] = y * w + x;

                    while (stack_top > 0) {
                        int index = stack[--stack_top];
                        int cx = index % w;
                        int cy = index / w;

                        if (IS_HOLE(cx, cy)) {
                            out[cy * w + cx] = 1.0;

                            for (int dir = 0; dir < 4; dir++) {
                                int nx = cx + dx[dir];
                                int ny = cy + dy[dir];
                                if (IS_HOLE(nx, ny)) {
                                    stack[stack_top++] = ny * w + nx;
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
