void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の外側は背景(0)とみなす
    // つまみ a, b は未使用

    // ヒット・オア・ミス変換を用いたモルフォロジー的細線化
    // ここでは単純な実装として、3x3 のマスクを用いて、
    // 画素が 1 で、その周囲の画素が特定のパターンに従って 0 である場合のみ、
    // その画素を 0 に変更する処理を繰り返す。

    // 一度の処理で削除できる画素を記録する配列
    int to_remove[h * w];
    int to_remove_count = 0;

    // マスクのパターンを定義
    // ここでは単純な例として、画素が 1 で、その周囲の画素が特定のパターンに従って 0 である場合のみ、
    // その画素を 0 に変更する処理を繰り返す。
    // 以下は単純な例であり、実際のアルゴリズムはより複雑なパターンを用いる。
    int mask[9] = {1, 0, 0, 1, 0, 1, 0, 1, 1};

    // 処理の繰り返し
    while (to_remove_count > 0) {
        to_remove_count = 0;

        // 画像の各画素に対して処理を行う
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                // 3x3 マスクを適用
                int mask_index = 0;
                int match = 1;
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        int nx = x + dx;
                        int ny = y + dy;
                        // 画像の外側は背景(0)とみなす
                        if (nx < 0 || nx >= w || ny < 0 || ny >= h) {
                            mask[mask_index] = 0;
                        } else {
                            mask[mask_index] = in[ny * w + nx];
                        }
                        mask_index++;
                    }
                }

                // マスクのパターンと一致するかチェック
                int pattern_index = 0;
                for (int i = 0; i < 9; i++) {
                    if (mask[i] != mask[pattern_index]) {
                        match = 0;
                        break;
                    }
                    pattern_index++;
                }

                // パターンに一致する場合、削除リストに追加
                if (match) {
                    to_remove[to_remove_count++] = y * w + x;
                }
            }
        }

        // 削除リストに基づいて画像を更新
        for (int i = 0; i < to_remove_count; i++) {
            out[to_remove[i]] = 0;
        }
    }

    // 入力画像を出力画像にコピー
    for (int i = 0; i < h * w; i++) {
        out[i] = in[i];
    }

    // 削除リストに基づいて画像を更新
    for (int i = 0; i < to_remove_count; i++) {
        out[to_remove[i]] = 0;
    }
}
