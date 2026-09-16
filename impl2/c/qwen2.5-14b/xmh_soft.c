void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 閾値は a * 0.5 で計算される。a は [0, 1] の範囲。
    double threshold = a * 0.5;

    // 画像の各画素に対して処理を行う。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int idx = y * w + x;
            double pixel = in[idx];

            // 範囲外の値を処理するためのクリッピング。
            if (pixel < 0) {
                pixel = 0;
            } else if (pixel > 1) {
                pixel = 1;
            }

            // ソフト閾値処理
            if (fabs(pixel) < threshold) {
                out[idx] = 0; // 閾値未満の絶対値を持つ画素を 0 に潰す。
            } else {
                // それ以外は閾値分だけ 0 に近づける。
                out[idx] = pixel - threshold * (pixel > 0 ? 1 : -1);
            }
        }
    }
}
