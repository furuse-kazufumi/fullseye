#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int r = 1 + (int)(a * 4); // 円板半径 r = 1 + int(a*4) (1〜5 画素)
    int sh = (int)((b - 0.5) * 6); // 列方向のずらし量 sh = int((b-0.5)*6) (-3〜3)

    // 一時的な出力配列を用意
    double temp[h * w];
    memset(temp, 0, sizeof(temp));

    // バイナリーダイレーションの実行
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] > 0.5) {
                for (int dy = -r; dy <= r; dy++) {
                    for (int dx = -r; dx <= r; dx++) {
                        if (dx * dx + dy * dy <= r * r) {
                            int ny = y + dy;
                            int nx = x + dx;
                            if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                                temp[ny * w + nx] = 1.0;
                            }
                        }
                    }
                }
            }
        }
    }

    // 列方向のずらし (np.roll の代わり)
    for (int y = 0; y < h; y++) {
        int ny = (y + sh + h) % h; // 端からはみ出た分は反対側に現れる
        for (int x = 0; x < w; x++) {
            out[ny * w + x] = temp[y * w + x];
        }
    }
}
