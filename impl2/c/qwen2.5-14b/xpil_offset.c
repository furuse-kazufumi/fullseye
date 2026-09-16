void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a と b をそれぞれ画像の幅と高さに対するシフト量に変換
    int shift_x = (int)(w * a);
    int shift_y = (int)(h * b);

    // シフト量が負の場合は、正の値に変換
    if (shift_x < 0) {
        shift_x += w;
    }
    if (shift_y < 0) {
        shift_y += h;
    }

    // 画像をトロイダルにシフト
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // シフト後の座標を計算
            int new_x = (x + shift_x) % w;
            int new_y = (y + shift_y) % h;

            // 出力画像に値を設定
            out[y * w + x] = in[new_y * w + new_x];
        }
    }
}
