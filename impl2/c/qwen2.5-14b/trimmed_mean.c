#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用。つまみ a は {0.1, 0.5, 0.9} の範囲で効果があると指定されているが、
    // 仕様書では具体的な効果が明記されていない。ここでは a の値を {0.1, 0.5, 0.9} の範囲で
    // 3 つの窓サイズ {3, 5, 7} のいずれかにマッピングし、それに対応するフィルタリングを行う。
    // 0.1 と 0.9 の間の値は線形補間で 3 と 7 の間の奇数窓サイズにマッピングする。
    int window_size = (a <= 0.25) ? 3 : (a <= 0.75) ? 5 : 7;

    // 窓サイズが奇数であることを確認
    if (window_size % 2 == 0) {
        window_size++;
    }

    // 窓の半径
    int radius = (window_size - 1) / 2;

    // 端の扱い: 端画素を重複させて折り返す
    // これは scipy の既定の border_mode "reflect" に従う。

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 画像の各画素について処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 窓内の画素値を格納する配列
            double window[window_size * window_size];
            int window_index = 0;

            // 窓内の画素値を取得
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 端の処理: 画像の端を重複させて折り返す
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;

                    window[window_index++] = in[ny * w + nx];
                }
            }

            // 窓内の画素値をソート
            qsort(window, window_size * window_size, sizeof(double), compare);

            // 20 パーセンタイルと 80 パーセンタイルの画素値を取得
            int index_20 = (int)(window_size * window_size * 0.2);
            int index_80 = (int)(window_size * window_size * 0.8);
            double value_20 = window[index_20];
            double value_80 = window[index_80];

            // 20 パーセンタイルと 80 パーセンタイルの平均を計算
            double trimmed_mean = (value_20 + value_80) / 2.0;

            // 出力画像に結果を格納
            out[y * w + x] = trimmed_mean;
        }
    }
}

// qsort の比較関数
int compare(const void* a, const void* b) {
    return (*(double*)a - *(double*)b);
}
