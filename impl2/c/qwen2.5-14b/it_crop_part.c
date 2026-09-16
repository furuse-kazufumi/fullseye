void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は [0,1] の範囲で、画像の中央の a 分の部分をクロップする。
    // b は無視される。
    // 画像の端をどのように処理するかは、ここでは画像の端を固定値 0 で埋める。

    int crop_h = h * a; // クロップ後の高さ
    int crop_w = w * a; // クロップ後の幅
    int start_y = (h - crop_h) / 2; // クロップ開始位置の y 座標
    int start_x = (w - crop_w) / 2; // クロップ開始位置の x 座標

    // リサンプリングのためのスケーリングファクター
    double scale_y = (double)h / crop_h;
    double scale_x = (double)w / crop_w;

    // 出力画像の各ピクセルを計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // クロップされた画像の座標を計算
            int crop_y = (y - start_y) * scale_y;
            int crop_x = (x - start_x) * scale_x;

            // 座標がクロップされた画像の範囲外の場合、固定値 0 を出力
            if (crop_y < 0 || crop_y >= crop_h || crop_x < 0 || crop_x >= crop_w) {
                out[y * w + x] = 0;
            } else {
                // 座標が範囲内の場合、入力画像から値を取得
                out[y * w + x] = in[(start_y + crop_y) * w + (start_x + crop_x)];
            }
        }
    }
}
