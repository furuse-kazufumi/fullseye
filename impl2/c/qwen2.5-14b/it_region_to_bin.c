void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の各ピクセルに対して閾値処理を行う
    // a は閾値、b は出力画像の輝度範囲を決定するパラメータ
    // 閾値以下は背景、閾値以上は前景として処理する
    // 画像の端の処理については、境界外アクセスを避けるため、
    // 画像の端のピクセルに対しては内部と同じ処理を行う（境界値を無視）

    double low = 0.5 - 0.5 * b;
    double high = 0.5 + 0.5 * b;

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            double pixel = in[idx];
            out[idx] = (pixel < a) ? low : high;
        }
    }
}
