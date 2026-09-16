void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // ピクセルのインデックス
            int idx = y * w + x;

            // 画像の端の処理: 端のピクセルはその値をそのまま使用する
            if (y == 0 || y == h - 1 || x == 0 || x == w - 1) {
                out[idx] = in[idx];
                continue;
            }

            // ここに Weickert の coherency-enhancing diffusion のアルゴリズムを実装する
            // 以下はサンプルコードであり、実際のアルゴリズムはより複雑になる可能性がある
            // ここでは簡単な例として、入力画像の値をそのまま出力画像にコピーする
            out[idx] = in[idx];
        }
    }
}
