void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の全画素数
    int num_pixels = h * w;

    // 各領域の面積を計算するための配列
    int max_area = 0;
    int* areas = (int*)malloc(num_pixels * sizeof(int));
    int* labels = (int*)malloc(num_pixels * sizeof(int));

    // 連結成分ラベリング
    int label = 1;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int idx = y * w + x;
            if (in[idx] > 0.5) {
                int up = y > 0 ? labels[(y - 1) * w + x] : 0;
                int left = x > 0 ? labels[y * w + x - 1] : 0;
                if (up == 0 && left == 0) {
                    labels[idx] = label++;
                } else if (up == 0) {
                    labels[idx] = left;
                } else if (left == 0) {
                    labels[idx] = up;
                } else {
                    labels[idx] = up == left ? up : label++;
                }
            }
        }
    }

    // 各ラベルの面積を計算
    for (int i = 0; i < num_pixels; i++) {
        areas[labels[i]]++;
    }

    // 最大面積のラベルを特定
    int max_label = 1;
    for (int i = 2; i < label; i++) {
        if (areas[i] > areas[max_label]) {
            max_label = i;
        }
    }
    max_area = areas[max_label];

    // 出力画像を生成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int idx = y * w + x;
            out[idx] = labels[idx] == max_label ? 1.0 : 0.0;
        }
    }

    // メモリを解放
    free(areas);
    free(labels);
}
