void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // b でどの方向を見るか選ぶ
    int direction = (int)(b * 3);
    direction = direction < 2 ? direction : 2; // cH (0), cV (1), cD (2)

    // 出力画像の高さと幅は入力画像の半分
    int oh = h / 2;
    int ow = w / 2;

    // 2x2 ブロック拡大を行うための内部関数
    void expand_block(const double* subband, int sh, int sw, double* out, int oh, int ow) {
        for (int y = 0; y < oh; ++y) {
            for (int x = 0; x < ow; ++x) {
                int sy = y / 2;
                int sx = x / 2;
                int sy_next = (sy + 1) % sh;
                int sx_next = (sx + 1) % sw;
                int sy_prev = (sy - 1 + sh) % sh;
                int sx_prev = (sx - 1 + sw) % sw;

                double value = 0.0;
                switch (direction) {
                    case 0: // cH
                        value = subband[sy * sw + sx];
                        break;
                    case 1: // cV
                        value = subband[sy * sw + sx];
                        break;
                    case 2: // cD
                        value = subband[sy * sw + sx];
                        break;
                }

                // 絶対値を取る
                value = fabs(value);

                // 正規化
                value /= (sh * sw);

                // 2x2 ブロックに展開
                out[y * ow * 4 + x * 4 + 0] = value;
                out[y * ow * 4 + x * 4 + 1] = value;
                out[y * ow * 4 + x * 4 + 2] = value;
                out[y * ow * 4 + x * 4 + 3] = value;
            }
        }
    }

    // 入力画像の半分の解像度のサブバンドを生成
    double* subband = (double*)malloc(oh * ow * sizeof(double));
    for (int y = 0; y < oh; ++y) {
        for (int x = 0; x < ow; ++x) {
            int sy = y * 2;
            int sx = x * 2;
            int sy_next = (sy + 1) % h;
            int sx_next = (sx + 1) % w;
            int sy_prev = (sy - 1 + h) % h;
            int sx_prev = (sx - 1 + w) % w;

            double value = 0.0;
            switch (direction) {
                case 0: // cH
                    value = in[sy * w + sx] - in[sy * w + sx_next];
                    break;
                case 1: // cV
                    value = in[sy * w + sx] - in[sy_next * w + sx];
                    break;
                case 2: // cD
                    value = in[sy * w + sx] - in[sy_next * w + sx_next];
                    break;
            }

            subband[y * ow + x] = value;
        }
    }

    // 2x2 ブロック拡大
    expand_block(subband, oh, ow, out, h, w);

    // メモリ解放
    free(subband);
}
