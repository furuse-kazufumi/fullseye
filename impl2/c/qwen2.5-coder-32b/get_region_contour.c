void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端をどう処理するか: 画像の端の画素は、その周囲にある画素と比較する際に存在しない画素を0と仮定する。
    // つまり、端の画素は内部の画素と同様に処理されるが、端の外側は0とみなされる。

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int index = y * w + x;
            if (in[index] == 1.0) {
                // Check the 8 neighbors
                int is_contour = 0;
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        if (dy == 0 && dx == 0) continue; // Skip the center pixel itself
                        int ny = y + dy;
                        int nx = x + dx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            if (in[ny * w + nx] == 0.0) {
                                is_contour = 1;
                                break;
                            }
                        } else {
                            // Out of bounds, consider as background (0.0)
                            is_contour = 1;
                            break;
                        }
                    }
                }
                out[index] = is_contour ? 1.0 : 0.0;
            } else {
                out[index] = 0.0;
            }
        }
    }
}
