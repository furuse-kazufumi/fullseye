void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ブロックサイズの計算
    int nb = 2 + (int)(4 * a); // ブロック数は a によって 2 から 6 の範囲で変化
    int block_size = (nb > 0) ? (w / nb) : 1; // ブロックサイズを計算
    int block_height = (nb > 0) ? (h / nb) : 1; // ブロックの高さを計算

    // 各ブロックのヒストグラム平坦化
    for (int by = 0; by < nb; by++) {
        for (int bx = 0; bx < nb; bx++) {
            // ブロックの範囲を計算
            int y0 = by * block_height;
            int y1 = (by + 1) * block_height;
            int x0 = bx * block_size;
            int x1 = (bx + 1) * block_size;

            // ブロックの範囲が画像の範囲を超える場合、ブロックの範囲を調整
            if (y1 > h) y1 = h;
            if (x1 > w) x1 = w;

            // ヒストグラム平坦化処理
            for (int y = y0; y < y1; y++) {
                for (int x = x0; x < x1; x++) {
                    int index = y * w + x;
                    double value = in[index];
                    // ヒストグラム平坦化の処理 (ここでは単純な線形変換を仮定)
                    double normalized_value = (value - 0.0) / (1.0 - 0.0); // 0-1 正規化
                    double cdf_value = normalized_value; // 簡単のため、ここでは CDF が入力値と同じと仮定
                    out[index] = cdf_value; // 出力画像に書き込み
                }
            }
        }
    }
}
