void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は 0 から 1 の範囲で、1 から 4 の反復回数にマッピングする。
    int iterations = (int)(a * 4 + 0.5); // 0.5 で丸める
    iterations = (iterations < 1) ? 1 : iterations; // 最小 1 回

    // 出力画像を入力画像と同じ値で初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 膨張処理を繰り返す
    for (int i = 0; i < iterations; i++) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                // 十字形構造要素を適用
                double max_val = in[y * w + x];
                if (y > 0) max_val = (in[(y - 1) * w + x] > max_val) ? in[(y - 1) * w + x] : max_val;
                if (y < h - 1) max_val = (in[(y + 1) * w + x] > max_val) ? in[(y + 1) * w + x] : max_val;
                if (x > 0) max_val = (in[y * w + x - 1] > max_val) ? in[y * w + x - 1] : max_val;
                if (x < w - 1) max_val = (in[y * w + x + 1] > max_val) ? in[y * w + x + 1] : max_val;

                // 結果を出力画像に書き込む
                out[y * w + x] = (max_val > 0) ? 1.0 : 0.0;
            }
        }
    }
}
