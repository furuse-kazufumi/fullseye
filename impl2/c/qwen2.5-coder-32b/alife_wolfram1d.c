#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Wolfram's elementary cellular automaton rules
    // We use a to select a rule from 0 to 255
    int rule = (int)(a * 255.0) & 0xFF;

    // Initialize the first row based on the input image thresholded at 0.5
    // If the first row is empty, use a single central seed
    int first_row[w];
    memset(first_row, 0, sizeof(first_row));
    int seed_count = 0;
    for (int x = 0; x < w; x++) {
        if (in[x] >= 0.5) {
            first_row[x] = 1;
            seed_count++;
        }
    }
    if (seed_count == 0) {
        // Use a single central seed
        first_row[w / 2] = 1;
    } else {
        // Add extra seeds based on b
        int extra_seeds = (int)(b * w / 2.0);
        for (int i = 0; i < extra_seeds; i++) {
            int pos = (i * w / extra_seeds) % w;
            first_row[pos] = 1;
        }
    }

    // Write the first row to the output
    for (int x = 0; x < w; x++) {
        out[x] = first_row[x];
    }

    // Generate subsequent rows using the selected rule
    for (int y = 1; y < h; y++) {
        int next_row[w];
        for (int x = 0; x < w; x++) {
            // Calculate the index for the rule
            int index = (first_row[(x - 1 + w) % w] << 2) |
                        (first_row[x] << 1) |
                        first_row[(x + 1) % w];
            // Apply the rule
            next_row[x] = (rule >> index) & 1;
        }
        // Write the next row to the output
        for (int x = 0; x < w; x++) {
            out[y * w + x] = next_row[x];
        }
        // Update the first row for the next iteration
        memcpy(first_row, next_row, sizeof(first_row));
    }
}
