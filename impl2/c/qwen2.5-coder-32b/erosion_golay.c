#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // パラメータ a を使用して円形構造要素の半径を決定
    int radius = (int)(a * 4.0); // a は [0,1] なので、半径は 0 から 4 まで
    if (radius < 1) radius = 1; // 半径が 0 の場合は 1 に設定

    // 出力画像を初期化 (0.0 で埋める)
    memset(out, 0, sizeof(double) * h * w);

    // 各画素に対して処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 入力画素が 1.0 でない場合はスキップ
            if (in[y * w + x] != 1.0) continue;

            // 円形構造要素の範囲内に画素が存在するかチェック
            int is_eroded = 1;
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 境界外アクセスを避ける
                    if (ny < 0 || ny >= h || nx < 0 || nx >= w) {
                        is_eroded = 0;
                        break;
                    }

                    // 円形構造要素内かチェック
                    if (dx * dx + dy * dy <= radius * radius) {
                        if (in[ny * w + nx] != 1.0) {
                            is_eroded = 0;
                            break;
                        }
                    }
                }
                if (!is_eroded) break;
            }

            // 円形構造要素内に全ての画素が存在すれば出力に 1.0 を設定
            if (is_eroded) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
