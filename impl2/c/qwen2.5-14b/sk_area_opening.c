void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 面積しきい値の計算
    int area_threshold = 16 + (int)(a * 100);

    // 4近傍の隣接画素のインデックス
    int neighbors[4][2] = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}};

    // 画像の端の画素は背景(0)とみなす
    // これは仕様書で明示的に指定されている処理方法です。

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 面積オープニング処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] > 0.5) { // 画素が明るい場合
                int area = 1; // 自身の画素をカウント
                int visited[h * w];
                int visited_count = 0;
                for (int i = 0; i < h * w; i++) {
                    visited[i] = 0;
                }
                visited[y * w + x] = 1;

                // 幅優先探索で連結画素をカウント
                int queue[h * w];
                int front = 0, rear = 0;
                queue[rear++] = y * w + x;
                while (front < rear) {
                    int current = queue[front++];
                    for (int i = 0; i < 4; i++) {
                        int ny = current / w + neighbors[i][0];
                        int nx = current % w + neighbors[i][1];
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w && in[ny * w + nx] > 0.5 && !visited[ny * w + nx]) {
                            visited[ny * w + nx] = 1;
                            queue[rear++] = ny * w + nx;
                            area++;
                        }
                    }
                }

                // 面積がしきい値未満の場合は画素を消す
                if (area < area_threshold) {
                    out[y * w + x] = 0.0;
                } else {
                    out[y * w + x] = in[y * w + x];
                }
            }
        }
    }
}
