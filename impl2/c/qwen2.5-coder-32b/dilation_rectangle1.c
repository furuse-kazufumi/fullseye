#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a が [0,1] の範囲なので、3, 5, 7, 9 のいずれかにスケーリングする。
    // ここでは a * 8 して四捨五入し、1 から 8 の値を得てから 2 ずつ増加させる。
    int side_length = (int)(a * 8 + 0.5);
    if (side_length < 1) side_length = 1;
    if (side_length > 4) side_length = 4;
    side_length = 2 * side_length + 1;

    // 矩形構造要素の半径
    int radius = side_length / 2;

    // 出力を初期化
    memset(out, 0, sizeof(double) * h * w);

    // 各画素に対して膨張処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] == 1.0) {
                // 矩形構造要素の範囲内で出力を 1.0 にする
                for (int dy = -radius; dy <= radius; dy++) {
                    for (int dx = -radius; dx <= radius; dx++) {
                        int ny = y + dy;
                        int nx = x + dx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            out[ny * w + nx] = 1.0;
                        }
                    }
                }
            }
        }
    }
}
