#include <math.h>

static int fs2_reflect_index(int i, int n)
{
    if (n <= 1)
        return 0;

    /*
     * 選択: reflect は端画素を重複する half-sample symmetric とする。
     * 例: [a b c] の外側は ... b a | a b c | c b ... となる。
     */
    while (i < 0 || i >= n) {
        if (i < 0)
            i = -i - 1;
        else
            i = n - 1 - (i - n);
    }
    return i;
}

void fs2_apply(const double* in, int h, int w,
               double a, double b, double* out)
{
    int y, x;
    const double scale = 0.7 + 0.6 * a;
    const double cy = 0.5 * (double)(h - 1);
    const double cx = 0.5 * (double)(w - 1);

    (void)b;

    /*
     * 仕様で未指定の補間法には双線形補間を選択する。
     * 画像中心は画素中心座標 ((w-1)/2, (h-1)/2) とする。
     * 0.5 しきい値では 0.5 以上を領域画素とする。
     * in と out は重ならないものとして処理する。
     */
    for (y = 0; y < h; ++y) {
        const double sy = cy + ((double)y - cy) / scale;
        const int y0_raw = (int)floor(sy);
        const int y1_raw = y0_raw + 1;
        const double fy = sy - (double)y0_raw;
        const int y0 = fs2_reflect_index(y0_raw, h);
        const int y1 = fs2_reflect_index(y1_raw, h);

        for (x = 0; x < w; ++x) {
            const double sx = cx + ((double)x - cx) / scale;
            const int x0_raw = (int)floor(sx);
            const int x1_raw = x0_raw + 1;
            const double fx = sx - (double)x0_raw;
            const int x0 = fs2_reflect_index(x0_raw, w);
            const int x1 = fs2_reflect_index(x1_raw, w);

            const double v00 = in[y0 * w + x0];
            const double v01 = in[y0 * w + x1];
            const double v10 = in[y1 * w + x0];
            const double v11 = in[y1 * w + x1];

            const double top = v00 + fx * (v01 - v00);
            const double bottom = v10 + fx * (v11 - v10);
            const double value = top + fy * (bottom - top);

            out[y * w + x] = (value >= 0.5) ? 1.0 : 0.0;
        }
    }
}
