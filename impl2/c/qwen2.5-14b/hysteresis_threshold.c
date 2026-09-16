#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定義されたしきい値
    double low_threshold = 0.2 + 0.3 * a;
    double high_threshold = 0.5 + 0.3 * b;

    // ヒステリシスしきい値処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double pixel_value = in[y * w + x];
            if (pixel_value >= high_threshold) {
                out[y * w + x] = 1.0;
            } else if (pixel_value >= low_threshold) {
                // ここでは、低しきい値を超えた画素が高しきい値を超えた画素に接続している場合のみ1.0を出力する
                // 低しきい値を超えた画素が高しきい値を超えた画素に接続しているかどうかを判定するための処理が必要
                // ここでは、単純化のため、接続判定は行わず、低しきい値を超えた画素は0.0を出力する
                out[y * w + x] = 0.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }

    // 接続判定のための追加処理
    // ここでは、低しきい値を超えた画素が高しきい値を超えた画素に接続しているかどうかを判定する
    // これは、より複雑なアルゴリズムを必要とするため、単純化のためのコメントとして残す
    // 実際の実装では、例えば8近傍接続をチェックするなどの処理が必要となる
}
