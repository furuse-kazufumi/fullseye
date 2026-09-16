void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端を背景(0)とみなす。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 3x3近傍に3つ以上の骨格画素を持つ画素(分岐点・交差点)を検出
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            if (in[y * w + x] == 1.0) {
                int count = 0;
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        if (in[(y + dy) * w + (x + dx)] == 1.0) {
                            count++;
                        }
                    }
                }
                // 自分自身もカウントされるので、3つ以上の近傍画素があるかどうかをチェック
                if (count >= 4) {
                    out[y * w + x] = 1.0;
                }
            }
        }
    }
}
