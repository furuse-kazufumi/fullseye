#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 線形運動ぼかしの長さと角度を計算
    int L = 3 + (int)(20 * a); // ぼかしの長さ
    L = (L % 2 == 0) ? L + 1 : L; // 奇数に保つ
    L = (L > h && h > 1) ? h - 1 : L; // 画像サイズを超えないようにする
    L = (L > w && w > 1) ? w - 1 : L;
    double angle = b * M_PI; // ぼかしの角度 (ラジアン)

    // ぼかしの方向ベクトルを計算
    double dx = cos(angle);
    double dy = sin(angle);

    // 出力画像を初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 線形運動ぼかしを適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;
            for (int i = -L / 2; i <= L / 2; i++) {
                int nx = x + (int)(dx * i);
                int ny = y + (int)(dy * i);
                // 反射境界を適用
                nx = (nx < 0) ? -nx : nx;
                nx = (nx >= w) ? 2 * w - 2 - nx : nx;
                ny = (ny < 0) ? -ny : ny;
                ny = (ny >= h) ? 2 * h - 2 - ny : ny;
                sum += in[ny * w + nx];
                count++;
            }
            out[y * w + x] = sum / count;
        }
    }
}
