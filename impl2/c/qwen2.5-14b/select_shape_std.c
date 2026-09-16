void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。この関数では無視する。

    // 連結成分のうち最大の面積を持つものだけを残す。
    // まず、入力画像のコピーを作成し、それを操作する。
    double* temp = (double*)malloc(h * w * sizeof(double));
    if (temp == NULL) {
        // メモリ確保失敗時の処理。ここでは単に終了する。
        return;
    }
    memcpy(temp, in, h * w * sizeof(double));

    // 連結成分のラベル付けを行う。
    int label = 1;
    int max_area = 0;
    int max_label = 0;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (temp[y * w + x] == 1.0) {
                // 連結成分の面積を計算し、最大の面積を持つラベルを記録する。
                int area = flood_fill(temp, h, w, y, x, label);
                if (area > max_area) {
                    max_area = area;
                    max_label = label;
                }
                label++;
            }
        }
    }

    // 最大の面積を持つラベルを持つ画素だけを残す。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (temp[y * w + x] == max_label) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }

    // メモリを解放する。
    free(temp);
}

// flood_fill 関数は、指定された位置から始まる連結成分のラベル付けと面積計算を行う。
// この関数は内部で使用される。
int flood_fill(double* img, int h, int w, int y, int x, int label) {
    if (y < 0 || y >= h || x < 0 || x >= w || img[y * w + x] != 1.0) {
        return 0;
    }
    img[y * w + x] = label;
    return 1 + flood_fill(img, h, w, y - 1, x, label) +
           flood_fill(img, h, w, y + 1, x, label) +
           flood_fill(img, h, w, y, x - 1, label) +
           flood_fill(img, h, w, y, x + 1, label);
}
