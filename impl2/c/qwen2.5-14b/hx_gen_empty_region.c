void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 仕様書によると、このオペレータは入力画像に関係なく空の領域を生成する。
    // つまり、出力は常に全画素が 0 の領域となる。
    // a, b パラメータは使用されない。

    // 出力配列を全 0 で初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = 0.0;
        }
    }
}
