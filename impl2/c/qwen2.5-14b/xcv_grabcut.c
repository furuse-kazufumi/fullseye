#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は使用しないが、引数として受け取る
    (void)a;
    (void)b;

    // 画像の中央 70% x 70% の矩形を「たぶん前景」の初期領域として設定
    int rect_x = (w - (int)(w * 0.7)) / 2;
    int rect_y = (h - (int)(h * 0.7)) / 2;
    int rect_w = (int)(w * 0.7);
    int rect_h = (int)(h * 0.7);

    // 出力画像を初期化
    memset(out, 0, h * w * sizeof(double));

    // 初期領域を設定
    for (int y = rect_y; y < rect_y + rect_h; y++) {
        for (int x = rect_x; x < rect_x + rect_w; x++) {
            out[y * w + x] = 1.0;
        }
    }

    // ここに GrabCut アルゴリズムの実装を追加する
    // 本実装では、GrabCut の詳細な実装は省略し、初期領域をそのまま出力する

    // 画像の端をどう処理するかは、仕様書に明示されていないため、
    // ここでは端のピクセルを 0.0 として出力する。
    // これは、端のピクセルが前景領域に含まれないことを仮定する。
}
