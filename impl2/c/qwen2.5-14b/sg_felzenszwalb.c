void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b の値を整数に変換
    int scale = 40 + (int)(a * 500); // scale の範囲は 40 から 540
    int min_size = 15 + (int)(b * 85); // min_size の範囲は 15 から 100

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0; // 初期値は 0.0
        }
    }

    // ここに Felzenszwalb のアルゴリズムの実装を追加する
    // ここでは単純な例として、全てのピクセルを 1.0 に設定する
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 1.0; // すべてのピクセルを 1.0 に設定
        }
    }
}
