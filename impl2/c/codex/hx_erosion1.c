void fs2_apply(const double* in, int h, int w,
               double a, double b, double* out)
{
    int x, y, dx, dy;
    int r = 1 + (int)(a * 4.0);
    int r2 = r * r;

    (void)b;

    /*
     * 円板は中心からのユークリッド距離が r 以下の画素で構成する。
     * 画像境界外は背景 (0.0) として扱う。
     * 仕様に別名使用の規定がないため、in と out は重ならないものとする。
     */
    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            int survives = 1;

            for (dy = -r; dy <= r && survives; ++dy) {
                for (dx = -r; dx <= r; ++dx) {
                    int nx, ny;

                    if (dx * dx + dy * dy > r2)
                        continue;

                    nx = x + dx;
                    ny = y + dy;

                    if (nx < 0 || nx >= w || ny < 0 || ny >= h ||
                        in[ny * w + nx] != 1.0) {
                        survives = 0;
                        break;
                    }
                }
            }

            out[y * w + x] = survives ? 1.0 : 0.0;
        }
    }
}
