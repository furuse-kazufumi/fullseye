#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Tolerance is calculated based on the parameter 'a' scaled between 0.05 and 0.35
    double tolerance = 0.05 + (a * 0.30);
    
    // Seed point is the center of the image
    int seed_x = w / 2;
    int seed_y = h / 2;
    double seed_value = in[seed_y * w + seed_x];
    
    // Initialize the output array with 0.0
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }
    
    // Stack for flood fill algorithm
    int* stack = (int*)malloc(h * w * sizeof(int));
    int stack_size = 0;
    
    // Push the seed point onto the stack
    stack[stack_size++] = seed_y * w + seed_x;
    out[seed_y * w + seed_x] = 1.0;
    
    // Directions for 4-connectivity (up, down, left, right)
    int directions[4][2] = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}};
    
    while (stack_size > 0) {
        // Pop a point from the stack
        int current = stack[--stack_size];
        int y = current / w;
        int x = current % w;
        
        // Check all 4-connected neighbors
        for (int d = 0; d < 4; d++) {
            int ny = y + directions[d][0];
            int nx = x + directions[d][1];
            
            // Check if the neighbor is within bounds
            if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                // Check if the neighbor has not been visited and is within tolerance
                if (out[ny * w + nx] == 0.0 && fabs(in[ny * w + nx] - seed_value) <= tolerance) {
                    stack[stack_size++] = ny * w + nx;
                    out[ny * w + nx] = 1.0;
                }
            }
        }
    }
    
    // Free the stack
    free(stack);
}
