void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 入力画像のピクセルを取得
            double pixel = in[y * w + x];
            
            // 出力画像のピクセルを設定
            // 仕様書では binarize とあるが、具体的な binarize のアルゴリズムが明記されていないため、
            // ここでは単純に閾値 0.5 を用いて 0 か 1 に変換する。
            out[y * w + x] = (pixel > 0.5) ? 1.0 : 0.0;
        }
    }
}
