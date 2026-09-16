void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は無視する
    if (a < 0.0 || a > 1.0) {
        a = 0.5; // a の範囲外の値が来た場合、0.5 にデフォルト値を設定
    }

    // a が 0 の場合、出力は全て 0 になる
    if (a == 0.0) {
        for (int i = 0; i < h * w; ++i) {
            out[i] = 0.0;
        }
        return;
    }

    // a が 1 の場合、出力は入力と同じ
    if (a == 1.0) {
        for (int i = 0; i < h * w; ++i) {
            out[i] = in[i];
        }
        return;
    }

    // a が 0 と 1 の間の場合、中央の a * 100% の領域を保持
    int crop_h = (int)(h * a);
    int crop_w = (int)(w * a);
    int start_y = (h - crop_h) / 2;
    int start_x = (w - crop_w) / 2;

    // 出力画像の中央 a * 100% の領域をコピー
    for (int y = 0; y < crop_h; ++y) {
        for (int x = 0; x < crop_w; ++x) {
            int in_index = (start_y + y) * w + (start_x + x);
            int out_index = y * crop_w + x;
            out[out_index] = in[in_index];
        }
    }

    // 出力画像の残りの領域を 0 で埋める
    for (int i = crop_h * crop_w; i < h * w; ++i) {
        out[i] = 0.0;
    }
}
