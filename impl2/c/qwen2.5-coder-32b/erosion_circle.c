#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a が構造要素の半径を 1〜4 の範囲で振る。b は未使用。
    int radius = (int)(1 + 3 * a); // a が [0,1] の範囲なので、半径は 1 から 4 になる。

    // 画像の端を処理する方法: 境界外の画素は 0 と仮定する。
    // これは HALCON の erosion_circle の動作に近い方法である。

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int is_foreground = 1;
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double distance = sqrt(dy * dy + dx * dx);
                        if (distance <= radius && in[ny * w + nx] == 0.0) {
                            is_foreground = 0;
                            break;
                        }
                    }
                }
                if (!is_foreground) break;
            }
            out[y * w + x] = is_foreground ? 1.0 : 0.0;
        }
    }
}
