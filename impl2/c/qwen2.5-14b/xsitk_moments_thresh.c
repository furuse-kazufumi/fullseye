void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ヒストグラムのビン数を計算
    int bin_count = (int)(a * 256); // 64〜256 の範囲に a をマッピング
    if (bin_count < 64) bin_count = 64;
    if (bin_count > 256) bin_count = 256;

    // ヒストグラムを初期化
    double histogram[bin_count];
    for (int i = 0; i < bin_count; i++) {
        histogram[i] = 0.0;
    }

    // ヒストグラムを作成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int index = (int)(in[y * w + x] * (bin_count - 1));
            histogram[index]++;
        }
    }

    // モーメントを計算
    double mean = 0.0;
    double variance = 0.0;
    double total = 0.0;
    for (int i = 0; i < bin_count; i++) {
        total += histogram[i];
        mean += i * histogram[i];
    }
    mean /= total;

    for (int i = 0; i < bin_count; i++) {
        variance += histogram[i] * (i - mean) * (i - mean);
    }
    variance /= total;

    // 閾値を計算
    double threshold = mean + sqrt(variance);

    // 二値化処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] < threshold) {
                out[y * w + x] = 0.0;
            } else {
                out[y * w + x] = 1.0;
            }
        }
    }
}
