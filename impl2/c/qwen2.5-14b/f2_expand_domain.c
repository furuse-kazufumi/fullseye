void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a はマージンの幅を設定する。b は無視される。
    int margin = (int)(a * 7); // 仕様書では a が 0 から 1 の範囲で、マージンの幅が 1 から 7 ピクセルであると指定されている。
    // マージンが 0 の場合は入力画像をそのまま出力する。
    if (margin == 0) {
        for (int i = 0; i < h * w; ++i) {
            out[i] = in[i];
        }
        return;
    }

    // 出力画像の各ピクセルを設定する。
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // マージン内では、最も近い既存のピクセルの値をコピーする。
            int ny = y - margin;
            int nx = x - margin;
            if (ny < 0 || ny >= h || nx < 0 || nx >= w) {
                // マージン外のピクセルは、最も近い既存のピクセルの値をコピーする。
                // ここでは、マージン外のピクセルは境界の値をコピーする。
                ny = (ny < 0) ? 0 : (ny >= h) ? h - 1 : ny;
                nx = (nx < 0) ? 0 : (nx >= w) ? w - 1 : nx;
            }
            out[y * w + x] = in[ny * w + nx];
        }
    }
}
