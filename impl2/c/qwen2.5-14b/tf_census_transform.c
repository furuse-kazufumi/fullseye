void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a 以外のパラメータは無視する
    // 端の扱い: BORDER_REFLECT_101 (端画素を重複させずに折り返す)

    // 画像の各ピクセルに対して census transform を適用
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 8近傍の各ピクセルに対して census transform を適用
            int census_value = 0;
            for (int dy = -1; dy <= 1; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    if (dx == 0 && dy == 0) continue; // 中心ピクセルは無視

                    // 端の扱い: BORDER_REFLECT_101
                    int nx = (x + dx + w) % w;
                    int ny = (y + dy + h) % h;
                    int nidx = ny * w + nx;
                    int cidx = y * w + x;

                    // 相対的な差分を計算
                    double center = in[cidx];
                    double neighbor = in[nidx];
                    double diff = center - neighbor;
                    double tolerance = a * center;

                    // 8ビットの census value を更新
                    if (diff > tolerance) {
                        census_value |= 1 << (abs(dx) * 2 + abs(dy) - 1);
                    }
                }
            }

            // 0..255 の census value を [0,1] の範囲に正規化
            out[y * w + x] = (double)census_value / 255.0;
        }
    }
}
