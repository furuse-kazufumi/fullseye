#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は [0, 1] の範囲で与えられる。座標に変換する。
    int x = (int)round(b * (w - 1));
    int y = (int)round(a * (h - 1));

    // 指定点が背景 (0) の場合、結果は空 (全て 0)。
    if (in[y * w + x] == 0.0) {
        for (int i = 0; i < h * w; ++i) {
            out[i] = 0.0;
        }
        return;
    }

    // 指定点が前景 (1) の場合、その連結成分だけを残す。
    // 連結成分の探索は幅優先探索 (BFS) を使用する。
    int* queue = (int*)malloc(h * w * sizeof(int));
    int* visited = (int*)calloc(h * w, sizeof(int));
    int front = 0, rear = 0;

    // 指定点をキューに追加
    queue[rear++] = y * w + x;
    visited[y * w + x] = 1;

    while (front < rear) {
        int current = queue[front++];
        int cy = current / w;
        int cx = current % w;

        // 現在の画素を出力に設定
        out[current] = 1.0;

        // 4 方向に隣接する画素をチェック
        for (int dy = -1; dy <= 1; ++dy) {
            for (int dx = -1; dx <= 1; ++dx) {
                if (abs(dy) + abs(dx) == 1) { // 4 方向の隣接画素
                    int ny = cy + dy;
                    int nx = cx + dx;

                    // 画像の範囲内に存在し、未訪問で前景画素である場合
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w &&
                        !visited[ny * w + nx] && in[ny * w + nx] == 1.0) {
                        queue[rear++] = ny * w + nx;
                        visited[ny * w + nx] = 1;
                    }
                }
            }
        }
    }

    free(queue);
    free(visited);
}
