#include <math.h>
#include <stdlib.h>
#include <string.h>

#define CLIP_LIMIT 256.0

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int nb = 2 + (int)(3 * a);
    int tile_h = h / nb;
    int tile_w = w / nb;
    int clip_limit = (int)(CLIP_LIMIT * b);

    // Allocate memory for histograms and CDFs
    int* histograms = (int*)calloc(nb * nb * 256, sizeof(int));
    double* cdfs = (double*)calloc(nb * nb * 256, sizeof(double));

    // Compute histograms for each tile
    for (int i = 0; i < nb; i++) {
        for (int j = 0; j < nb; j++) {
            int* hist = histograms + (i * nb + j) * 256;
            int start_y = i * tile_h;
            int end_y = (i == nb - 1) ? h : (i + 1) * tile_h;
            int start_x = j * tile_w;
            int end_x = (j == nb - 1) ? w : (j + 1) * tile_w;

            for (int y = start_y; y < end_y; y++) {
                for (int x = start_x; x < end_x; x++) {
                    int bin = (int)(in[y * w + x] * 255.0);
                    hist[bin]++;
                }
            }

            // Apply clip limit
            for (int k = 0; k < 256; k++) {
                if (hist[k] > clip_limit) {
                    hist[k] = clip_limit;
                }
            }

            // Compute CDF for the tile
            double* cdf = cdfs + (i * nb + j) * 256;
            cdf[0] = (double)hist[0] / (end_y - start_y) / (end_x - start_x);
            for (int k = 1; k < 256; k++) {
                cdf[k] = cdf[k - 1] + (double)hist[k] / (end_y - start_y) / (end_x - start_x);
            }
        }
    }

    // Apply CLAHE to each pixel
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double val = in[y * w + x] * 255.0;
            int bin = (int)val;
            double interpolated_val = 0.0;

            // Determine the tile indices
            int tile_y = y / tile_h;
            int tile_x = x / tile_w;

            // Bilinear interpolation of CDF values
            for (int i = 0; i < 2; i++) {
                for (int j = 0; j < 2; j++) {
                    int ny = tile_y + i;
                    int nx = tile_x + j;
                    if (ny >= nb) ny = nb - 1;
                    if (nx >= nb) nx = nb - 1;

                    double* cdf = cdfs + (ny * nb + nx) * 256;
                    double cdf_val = cdf[bin];
                    double weight = 1.0;

                    if (i == 1) weight *= (y - tile_y * tile_h) / (double)tile_h;
                    else weight *= (1.0 - (y - tile_y * tile_h) / (double)tile_h);

                    if (j == 1) weight *= (x - tile_x * tile_w) / (double)tile_w;
                    else weight *= (1.0 - (x - tile_x * tile_w) / (double)tile_w);

                    interpolated_val += cdf_val * weight;
                }
            }

            out[y * w + x] = interpolated_val;
        }
    }

    // Free allocated memory
    free(histograms);
    free(cdfs);
}
