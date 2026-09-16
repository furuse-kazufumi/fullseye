void fs2_apply(const double* in, int h, int w,
               double a, double b, double* out)
{
    int y, x, dy, dx;

    (void)a;
    (void)b;

    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            int neighbors = 0;

            if (in[y * w + x] == 0.0) {
                out[y * w + x] = 0.0;
                continue;
            }

            /*
             * 「3x3近傍」は中心画素を除く8近傍と解釈する。
             * 画像外は仕様どおり背景(0)として数えない。
             */
            for (dy = -1; dy <= 1; ++dy) {
                int ny = y + dy;

                if (ny < 0 || ny >= h)
                    continue;

                for (dx = -1; dx <= 1; ++dx) {
                    int nx = x + dx;

                    if (dy == 0 && dx == 0)
                        continue;
                    if (nx < 0 || nx >= w)
                        continue;

                    if (in[ny * w + nx] != 0.0)
                        ++neighbors;
                }
            }

            out[y * w + x] = (neighbors >= 3) ? 1.0 : 0.0;
        }
    }
}
