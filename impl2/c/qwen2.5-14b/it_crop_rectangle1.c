void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は [0,1] の範囲で、画像の中心部を切り出す範囲を決定します。b は無視します。
    // 画像の端をどのように処理するかについては、ここでは境界外のピクセルを補間せずに
    // 画像の端の値を保持します。つまり、切り出し範囲が画像の外に出た場合、その部分は
    // 画像の端の値で埋められます。

    int new_h = h * (1 - a);
    int new_w = w * (1 - a);
    int half_new_h = new_h / 2;
    int half_new_w = new_w / 2;
    int half_h = h / 2;
    int half_w = w / 2;

    // 中心部の矩形を切り出す
    for (int y = 0; y < new_h; y++) {
        for (int x = 0; x < new_w; x++) {
            int src_y = half_h + (y - half_new_h) / (1 - a);
            int src_x = half_w + (x - half_new_w) / (1 - a);

            // 画像の端を超えないようにする
            if (src_y < 0) src_y = 0;
            if (src_y >= h) src_y = h - 1;
            if (src_x < 0) src_x = 0;
            if (src_x >= w) src_x = w - 1;

            out[y * new_w + x] = in[src_y * w + src_x];
        }
    }

    // 切り出した矩形を元のサイズにリサンプリングする
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int dst_y = y * (new_h - 1) / (h - 1);
            int dst_x = x * (new_w - 1) / (w - 1);

            out[y * w + x] = out[dst_y * new_w + dst_x];
        }
    }
}
