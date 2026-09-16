void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a の値によって鏡映モードを決定
    int mode = (a < 0.34) ? 0 : ((a < 0.67) ? 1 : 2);

    // 出力画像の初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = 0.0;
        }
    }

    // 鏡映処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int out_y = y;
            int out_x = x;
            switch (mode) {
                case 0: // 上下反転
                    out_y = h - y - 1;
                    break;
                case 1: // 左右反転
                    out_x = w - x - 1;
                    break;
                case 2: // 転置
                    out_y = x;
                    out_x = y;
                    break;
            }
            // 出力画像の範囲内に確保
            if (out_y >= 0 && out_y < h && out_x >= 0 && out_x < w) {
                out[y * w + x] = in[out_y * w + out_x];
            }
        }
    }
}
