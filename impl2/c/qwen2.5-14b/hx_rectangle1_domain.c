void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // このオペレータは入力画像の内容を無視し、中央の矩形領域を1.0で埋め、それ以外を0.0で埋める。
    // a, b は矩形の高さと幅の割合を決定するパラメータで、[0,1]の範囲を取る。
    // a と b の値は 0.2 から 0.9 の範囲にマッピングされる。

    int hh = (int)(h * (0.2 + 0.7 * a)); // 高さの割合
    int ww = (int)(w * (0.2 + 0.7 * b)); // 幅の割合

    // 中央の矩形領域を計算
    int y0 = (h - hh) / 2;
    int x0 = (w - ww) / 2;

    // 出力画像を初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = 0.0; // 初期値は0.0
        }
    }

    // 中央の矩形領域を1.0で埋める
    for (int y = y0; y < y0 + hh; ++y) {
        for (int x = x0; x < x0 + ww; ++x) {
            out[y * w + x] = 1.0;
        }
    }
}
