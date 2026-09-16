void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 端の画素を複製するためのパディング処理
    // 画像の端を最近傍の画素値で埋める
    // 画像の端の処理は、入力画像の端の値を複製する

    // 出力画像の初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 画像の各画素に対して GrayscaleGrindPeak 操作を適用
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            // 局所的な8近傍の画素値を取得
            double local_min = in[(y - 1) * w + (x - 1)];
            double local_max = in[(y - 1) * w + (x - 1)];
            for (int dy = -1; dy <= 1; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    if (dy == 0 && dx == 0) continue; // 自身の画素はスキップ
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny < 0 || ny >= h || nx < 0 || nx >= w) continue; // 端の画素はスキップ
                    local_min = fmin(local_min, in[ny * w + nx]);
                    local_max = fmax(local_max, in[ny * w + nx]);
                }
            }
            // 局所的な最小値と最大値を比較し、削り落とす
            if (in[y * w + x] > local_max) {
                out[y * w + x] = local_max;
            } else if (in[y * w + x] < local_min) {
                out[y * w + x] = local_min;
            }
        }
    }

    // 端の画素を複製
    for (int y = 0; y < h; ++y) {
        out[y * w] = out[y * w + 1];
        out[y * w + w - 1] = out[y * w + w - 2];
    }
    for (int x = 0; x < w; ++x) {
        out[(h - 1) * w + x] = out[(h - 2) * w + x];
        out[x] = out[w + x];
    }
    out[0] = out[w];
    out[h * w - 1] = out[h * w - w - 1];
}
