#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const int N = 1 + (int)(400 * a);  // ステップ数
    const int initial_heading = (int)(b * 4);  // 初期向き (0: 上, 1: 右, 2: 下, 3: 左)
    const int dx[] = {0, 1, 0, -1};  // x 方向の移動ベクトル
    const int dy[] = {1, 0, -1, 0};  // y 方向の移動ベクトル
    const int turn_right[] = {1, 3, 0, 2};  // 右に曲がる後の向き
    const int turn_left[] = {3, 0, 1, 2};  // 左に曲がる後の向き

    // 初期化
    int x = w / 2, y = h / 2;  // アントの初期位置
    int heading = initial_heading;  // アントの初期向き
    int grid[h][w];  // グリッドの状態 (0: 白, 1: 黒)

    // グリッドの初期化 (全てのセルを白に)
    for (int i = 0; i < h; i++) {
        for (int j = 0; j < w; j++) {
            grid[i][j] = (in[i * w + j] >= 0.5) ? 1 : 0;
        }
    }

    // アントの移動ループ
    for (int step = 0; step < N; step++) {
        // セルの色を反転
        grid[y][x] = 1 - grid[y][x];

        // 方向を変更
        if (grid[y][x] == 0) {
            heading = turn_right[heading];
        } else {
            heading = turn_left[heading];
        }

        // アントを移動
        x = (x + dx[heading] + w) % w;  // x 座標の更新 (トーラス境界条件)
        y = (y + dy[heading] + h) % h;  // y 座標の更新 (トーラス境界条件)
    }

    // 出力画像の生成
    for (int i = 0; i < h; i++) {
        for (int j = 0; j < w; j++) {
            out[i * w + j] = grid[i][j];
        }
    }
}
