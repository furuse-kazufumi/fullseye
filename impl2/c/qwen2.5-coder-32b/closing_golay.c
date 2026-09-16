#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // パラメータ a を使用して円形構造要素の半径を決定
    int radius = (int)(a * 4.0); // a は [0,1] なので、半径は 0 から 4 まで
    if (radius < 1) radius = 1; // 半径が 0 の場合は 1 に設定

    // 構造要素のサイズを計算
    int se_size = 2 * radius + 1;
    int se_area = se_size * se_size;

    // 構造要素の中心位置
    int se_center = radius;

    // 一時的な出力バッファを確保
    double* temp = (double*)malloc(h * w * sizeof(double));
    if (temp == NULL) return; // メモリ確保に失敗した場合は終了

    // 膨張処理 (dilation)
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            temp[y * w + x] = 0.0;
            for (int sy = -radius; sy <= radius; sy++) {
                for (int sx = -radius; sx <= radius; sx++) {
                    int ny = y + sy;
                    int nx = x + sx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (in[ny * w + nx] == 1.0) {
                            temp[y * w + x] = 1.0;
                            break;
                        }
                    }
                }
                if (temp[y * w + x] == 1.0) break;
            }
        }
    }

    // 収縮処理 (erosion)
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 1.0;
            for (int sy = -radius; sy <= radius; sy++) {
                for (int sx = -radius; sx <= radius; sx++) {
                    int ny = y + sy;
                    int nx = x + sx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (temp[ny * w + nx] == 0.0) {
                            out[y * w + x] = 0.0;
                            break;
                        }
                    } else {
                        out[y * w + x] = 0.0;
                        break;
                    }
                }
                if (out[y * w + x] == 0.0) break;
            }
        }
    }

    // 一時的な出力バッファを解放
    free(temp);
}
