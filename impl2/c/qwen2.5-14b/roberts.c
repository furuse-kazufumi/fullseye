void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用
    (void)a;
    (void)b;

    // 出力画像の最大値を初期化
    double max_output = 0.0;

    // 画像の端をエッジ複製で処理
    // 2x2 のカーネルを使用するため、出力画像のサイズは入力画像と同じ
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // Roberts クロス演算子の計算
            double dx = in[(y + 1) * w + (x + 1)] - in[y * w + x];
            double dy = in[y * w + (x + 1)] - in[(y + 1) * w + x];
            double edge = hypot(dx, dy);

            // 出力画像の最大値を更新
            if (edge > max_output) {
                max_output = edge;
            }

            // 出力画像に結果を格納
            out[y * w + x] = edge;
        }
    }

    // 出力を最大値で正規化
    if (max_output > 0.0) {
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                out[y * w + x] /= max_output;
            }
        }
    }
}
