#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素のサイズを計算
    int se_size = 3 + 2 * (int)(a * 3);
    // 構造要素の半径
    int se_radius = se_size / 2;

    // ブラックハット変換のためのモルフォロジー演算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 最大値を初期化
            double max_val = in[y * w + x];
            // 構造要素の範囲内の画素をチェック
            for (int dy = -se_radius; dy <= se_radius; ++dy) {
                for (int dx = -se_radius; dx <= se_radius; ++dx) {
                    // 画像の端の処理: 端画素を重複させて折り返す
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;
                    // 最大値を更新
                    max_val = fmax(max_val, in[ny * w + nx]);
                }
            }
            // ブラックハット変換の結果を計算
            out[y * w + x] = max_val - in[y * w + x];
        }
    }

    // 正規化: 出力をその画像の最大値で正規化
    double max_out = 0.0;
    for (int i = 0; i < h * w; ++i) {
        max_out = fmax(max_out, out[i]);
    }
    if (max_out > 0.0) {
        for (int i = 0; i < h * w; ++i) {
            out[i] /= max_out;
        }
    }
}
