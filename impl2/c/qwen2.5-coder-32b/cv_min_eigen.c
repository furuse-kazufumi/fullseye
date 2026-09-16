#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ブロックサイズの計算 (3, 5, 7 のいずれか)
    int blockSize = 3 + 2 * (int)(a * 2);
    int halfSize = blockSize / 2;

    // 画像の端をどう処理するか: 境界外のピクセルにはゼロを仮定する
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sumIxx = 0.0, sumIyy = 0.0, sumIxy = 0.0;

            for (int ky = -halfSize; ky <= halfSize; ky++) {
                for (int kx = -halfSize; kx <= halfSize; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // 境界外のピクセルにはゼロを仮定
                    double pixel = (ny >= 0 && ny < h && nx >= 0 && nx < w) ? in[ny * w + nx] : 0.0;

                    // 勾配の計算
                    double dx = (nx + 1 < w) ? in[ny * w + nx + 1] - pixel : 0.0;
                    double dy = (ny + 1 < h) ? in[(ny + 1) * w + nx] - pixel : 0.0;

                    // 構造テンソルの要素の累積
                    sumIxx += dx * dx;
                    sumIyy += dy * dy;
                    sumIxy += dx * dy;
                }
            }

            // 固有値の計算
            double trace = sumIxx + sumIyy;
            double det = sumIxx * sumIyy - sumIxy * sumIxy;
            double eigen1 = 0.5 * (trace + sqrt(trace * trace - 4 * det));
            double eigen2 = 0.5 * (trace - sqrt(trace * trace - 4 * det));

            // 最小固有値を選択
            double minEigen = fmin(eigen1, eigen2);

            // 正規化 (0 から 1 に収める)
            out[y * w + x] = fmin(fmax(minEigen, 0.0), 1.0);
        }
    }
}
