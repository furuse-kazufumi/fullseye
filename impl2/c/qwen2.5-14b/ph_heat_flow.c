void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 辺の境界をどのように扱うかの選択: ここでは、境界の値をそのまま使用する。
    // これは、画像の端を固定する効果があり、拡散が端に達したときに止まる。

    // テンポラリ配列を確保
    double *temp = (double*)malloc(h * w * sizeof(double));
    if (temp == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // 初期化: 出力画像を入力画像と同じにする
    for (int i = 0; i < h * w; ++i) {
        out[i] = in[i];
    }

    // 拡散ステップの数を計算
    int steps = (int)(a * 10); // a は [0,1] の範囲で、10ステップを最大とする

    // 各ステップで拡散を適用
    for (int step = 0; step < steps; ++step) {
        // 5点ステンシルを使用して各ピクセルの新しい値を計算
        for (int y = 1; y < h - 1; ++y) {
            for (int x = 1; x < w - 1; ++x) {
                int idx = y * w + x;
                temp[idx] = 0.2 * (in[idx] + in[idx - 1] + in[idx + 1] + in[idx - w] + in[idx + w]);
            }
        }

        // テンポラリ配列から出力画像に結果をコピー
        for (int i = 0; i < h * w; ++i) {
            out[i] = temp[i];
        }

        // 入力画像を更新
        for (int i = 0; i < h * w; ++i) {
            in[i] = out[i];
        }
    }

    // テンポラリ配列を解放
    free(temp);
}
