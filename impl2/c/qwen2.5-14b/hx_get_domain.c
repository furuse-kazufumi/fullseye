void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // このオペレータは入力画像の定義域を取得するが、
    // 画像にROIの概念がないため、常に全面を返す。
    // そのため、出力は全1の配列となる。
    // a, b パラメータは使用しない。

    // 出力配列を全1に初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = 1.0;
        }
    }
}
