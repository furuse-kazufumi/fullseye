void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // マスクウィンドウのサイズを計算
    int mask_size = (int)(a * (h < w ? h : w));
    int mask_half = mask_size / 2;

    // マスクウィンドウの外側の境界を計算
    int left = mask_half;
    int right = w - mask_half;
    int top = mask_half;
    int bottom = h - mask_half;

    // 出力画像を入力画像と同じにする
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // マスクウィンドウ内の各ピクセルについて、境界値を考慮しながら平滑化
    for (int iter = 0; iter < 100; iter++) { // 100 回の反復
        for (int y = top; y < bottom; y++) {
            for (int x = left; x < right; x++) {
                double sum = 0.0;
                int count = 0;

                // 4-近傍のピクセルを取得
                if (y > top && x > left) {
                    sum += out[(y - 1) * w + (x - 1)];
                    count++;
                }
                if (y > top) {
                    sum += out[(y - 1) * w + x];
                    count++;
                }
                if (x < right - 1 && y > top) {
                    sum += out[(y - 1) * w + (x + 1)];
                    count++;
                }
                if (x > left) {
                    sum += out[y * w + (x - 1)];
                    count++;
                }
                if (x < right - 1) {
                    sum += out[y * w + (x + 1)];
                    count++;
                }
                if (y < bottom - 1 && x > left) {
                    sum += out[(y + 1) * w + (x - 1)];
                    count++;
                }
                if (y < bottom - 1) {
                    sum += out[(y + 1) * w + x];
                    count++;
                }
                if (y < bottom - 1 && x < right - 1) {
                    sum += out[(y + 1) * w + (x + 1)];
                    count++;
                }

                // 4-近傍の平均値を計算
                if (count > 0) {
                    out[y * w + x] = sum / count;
                }
            }
        }
    }
}
