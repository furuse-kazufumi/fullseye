void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int x, y;
    int dx = (int)(b * w);
    int dy = (int)(a * h);

    // 端は循環するように処理
    for (y = 0; y < h; y++) {
        for (x = 0; x < w; x++) {
            int new_x = (x + dx) % w;
            int new_y = (y + dy) % h;
            if (new_x < 0) new_x += w;
            if (new_y < 0) new_y += h;
            out[y * w + x] = in[new_y * w + new_x];
        }
    }
}
