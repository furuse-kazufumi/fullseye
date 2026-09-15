#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Initialize the output image to the same as the input image
    memcpy(out, in, h * w * sizeof(double));

    // Calculate the number of steps
    int N = 1 + (int)(400.0 * a);

    // Determine the initial direction based on b
    int direction = (int)(4.0 * b) % 4; // 0: up, 1: right, 2: down, 3: left

    // Define direction vectors for up, right, down, left
    int dx[] = {0, 1, 0, -1};
    int dy[] = {-1, 0, 1, 0};

    // Start position at the center of the grid
    int x = w / 2;
    int y = h / 2;

    for (int step = 0; step < N; step++) {
        // Calculate the index of the current cell
        int index = y * w + x;

        // Determine the color of the current cell
        int color = (out[index] >= 0.5) ? 1 : 0;

        // Flip the color of the current cell
        out[index] = 1.0 - out[index];

        // Update the direction based on the color
        if (color == 0) {
            direction = (direction + 1) % 4; // Turn right
        } else {
            direction = (direction + 3) % 4; // Turn left
        }

        // Move to the next cell
        x = (x + dx[direction] + w) % w;
        y = (y + dy[direction] + h) % h;
    }
}
