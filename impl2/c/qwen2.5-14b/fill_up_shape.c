#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 領域の面積閾値を計算
    int area_threshold = 16 + (int)(200 * a);

    // 出力画像を入力画像と同じにする
    memcpy(out, in, h * w * sizeof(double));

    // 8近傍を考慮するための配列
    int dx[] = {-1, -1, -1, 0, 0, 1, 1, 1};
    int dy[] = {-1, 0, 1, -1, 1, -1, 0, 1};

    // 画像の各画素をチェック
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] == 1.0) {
                int hole_size = 0;
                // 8近傍の画素をチェック
                for (int i = 0; i < 8; i++) {
                    int ny = y + dy[i];
                    int nx = x + dx[i];
                    // 画像の範囲内にいるかチェック
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (in[ny * w + nx] == 0.0) {
                            hole_size++;
                        }
                    }
                }
                // 穴の面積が閾値以下であれば穴を埋める
                if (hole_size <= area_threshold) {
                    for (int i = 0; i < 8; i++) {
                        int ny = y + dy[i];
                        int nx = x + dx[i];
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            if (in[ny * w + nx] == 0.0) {
                                out[ny * w + nx] = 1.0;
                            }
                        }
                    }
                }
            }
        }
    }
}
