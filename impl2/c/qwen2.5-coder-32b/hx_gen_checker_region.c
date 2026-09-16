void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Calculate the cell size based on the parameter 'a'
    // 'a' is scaled to be between 5% and 25% of the minimum dimension of the image
    int min_dim = (h < w) ? h : w;
    int cell_size = (int)(min_dim * (0.05 + 0.20 * a));

    // Ensure cell_size is at least 1
    if (cell_size < 1) {
        cell_size = 1;
    }

    // Generate the checkerboard pattern
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // Determine if the cell is part of the foreground (1) or background (0)
            int row_cell = y / cell_size;
            int col_cell = x / cell_size;
            if ((row_cell + col_cell) % 2 == 0) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }
}
