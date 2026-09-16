#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は正方形の構造要素のサイズを決定する。b は無視する。
    int struct_size = (int)(a * 9); // a が 0.1 から 0.9 の範囲で動くと、構造要素のサイズは 3 から 9 まで変化する。
    if (struct_size % 2 == 0) {
        struct_size++; // 結構要素のサイズは奇数でなければならない。
    }

    // 出力画像を入力画像と同じサイズで初期化
    memset(out, 0, h * w * sizeof(double));

    // マスクの中心位置
    int center = struct_size / 2;

    // 各画素についてオープニング処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 結構要素が完全に画像内に収まる場合のみオープニング処理を行う
            if (y - center >= 0 && y + center < h && x - center >= 0 && x + center < w) {
                int min_val = 1;
                // 結構要素の範囲内の画素について最小値を計算
                for (int dy = -center; dy <= center; dy++) {
                    for (int dx = -center; dx <= center; dx++) {
                        int nx = x + dx;
                        int ny = y + dy;
                        if (in[ny * w + nx] == 0) {
                            min_val = 0;
                            break;
                        }
                    }
                    if (min_val == 0) break;
                }
                out[y * w + x] = min_val;
            } else {
                // 結構要素が画像の外に出る場合は、元の画素値を出力にコピー
                out[y * w + x] = in[y * w + x];
            }
        }
    }
}
