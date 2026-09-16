#include <math.h>
#include <stdlib.h>
#include <string.h>

#define CLIP_LIMIT_MIN 1.0
#define CLIP_LIMIT_MAX 5.0
#define TILE_SIZE 8

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int tile_h = (h + TILE_SIZE - 1) / TILE_SIZE;
    int tile_w = (w + TILE_SIZE - 1) / TILE_SIZE;
    double clip_limit = CLIP_LIMIT_MIN + a * (CLIP_LIMIT_MAX - CLIP_LIMIT_MIN);

    // Allocate histogram and cumulative histogram arrays
    int* histograms = (int*)calloc(tile_h * tile_w * 256, sizeof(int));
    int* cumulative_histograms = (int*)calloc(tile_h * tile_w * 256, sizeof(int));

    // Calculate histograms for each tile
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int tile_y = y / TILE_SIZE;
            int tile_x = x / TILE_SIZE;
            int bin = (int)(in[y * w + x] * 255.0);
            histograms[(tile_y * tile_w + tile_x) * 256 + bin]++;
        }
    }

    // Apply clip limit and calculate cumulative histograms
    for (int tile_y = 0; tile_y < tile_h; tile_y++) {
        for (int tile_x = 0; tile_x < tile_w; tile_x++) {
            int* hist = &histograms[(tile_y * tile_w + tile_x) * 256];
            int* cum_hist = &cumulative_histograms[(tile_y * tile_w + tile_x) * 256];
            int clip_count = 0;

            // Clip histogram
            for (int i = 0; i < 256; i++) {
                if (hist[i] > clip_limit) {
                    clip_count += hist[i] - clip_limit;
                    hist[i] = (int)clip_limit;
                }
            }

            // Distribute clipped values
            int extra = clip_count / 256;
            int remainder = clip_count % 256;
            for (int i = 0; i < 256; i++) {
                hist[i] += extra;
                if (i < remainder) {
                    hist[i]++;
                }
            }

            // Calculate cumulative histogram
            cum_hist[0] = hist[0];
            for (int i = 1; i < 256; i++) {
                cum_hist[i] = cum_hist[i - 1] + hist[i];
            }
        }
    }

    // Apply CLAHE to each pixel
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int tile_y = y / TILE_SIZE;
            int tile_x = x / TILE_SIZE;
            int bin = (int)(in[y * w + x] * 255.0);
            int* cum_hist = &cumulative_histograms[(tile_y * tile_w + tile_x) * 256];

            // Bilinear interpolation for sub-tile positions
            double sub_y = (y % TILE_SIZE) / (double)TILE_SIZE;
            double sub_x = (x % TILE_SIZE) / (double)TILE_SIZE;

            int top_left = (tile_y > 0 && tile_x > 0) ? cumulative_histograms[((tile_y - 1) * tile_w + (tile_x - 1)) * 256 + bin] : 0;
            int top_right = (tile_y > 0) ? cumulative_histograms[((tile_y - 1) * tile_w + tile_x) * 256 + bin] : 0;
            int bottom_left = (tile_x > 0) ? cumulative_histograms[(tile_y * tile_w + (tile_x - 1)) * 256 + bin] : 0;
            int bottom_right = cum_hist[bin];

            double interpolated = (1 - sub_y) * (1 - sub_x) * top_left +
                                  (1 - sub_y) * sub_x * top_right +
                                  sub_y * (1 - sub_x) * bottom_left +
                                  sub_y * sub_x * bottom_right;

            out[y * w + x] = interpolated / (TILE_SIZE * TILE_SIZE * clip_limit);
        }
    }

    // Free allocated memory
    free(histograms);
    free(cumulative_histograms);
}
