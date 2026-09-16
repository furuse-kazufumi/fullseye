#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用。a は半径のスケーリングファクターとして使用。
    int radius = (int)(a * 4); // 半径は 0 から 4 まで。a が 0.5 のとき半径は 2。
    if (radius < 0) radius = 0; // 半径は非負である。
    if (radius > 4) radius = 4; // 半径は最大 4 まで。

    // 出力画像を初期化。全ての画素を背景（0）に設定。
    memset(out, 0, h * w * sizeof(double));

    // 円形構造要素による収縮を実装。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 円形構造要素の中心が (x, y) のとき、その構造要素内の全ての画素をチェック。
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    // 円形構造要素の画素 (dx, dy) が円内にあるかチェック。
                    if (dx * dx + dy * dy <= radius * radius) {
                        int nx = x + dx;
                        int ny = y + dy;
                        // 画像の外側は背景（0）とみなす。
                        if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                            // 入力画像の画素が 1 である場合、出力画像の画素も 1 に設定。
                            if (in[ny * w + nx] == 1.0) {
                                out[y * w + x] = 1.0;
                                break; // 一度 1 に設定したら、他の画素はチェックしない。
                            }
                        }
                    }
                }
            }
        }
    }
}
