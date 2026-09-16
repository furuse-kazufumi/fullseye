#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 状態数 N の計算
    int N = 3 + (int)(9 * a);
    
    // ステップ数の計算
    int steps = 1 + (int)(15 * b);

    // 画像の各ピクセルに対して処理を実行
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 入力画像の現在のピクセルの値を取得
            double current_value = in[y * w + x];
            
            // 現在のピクセルの状態を計算
            int current_state = (int)(current_value * (N - 1));
            
            // 8近傍の状態を取得
            int neighbor_states[8];
            for (int i = 0; i < 8; i++) {
                int ny = y + (i / 3 - 1);
                int nx = x + (i % 3 - 1);
                // 周期境界条件を適用
                if (ny < 0) ny += h;
                if (nx < 0) nx += w;
                if (ny >= h) ny -= h;
                if (nx >= w) nx -= w;
                neighbor_states[i] = (int)(in[ny * w + nx] * (N - 1));
            }
            
            // 次の状態を計算
            int next_state = current_state;
            for (int i = 0; i < 8; i++) {
                if (neighbor_states[i] == (current_state + 1) % N) {
                    next_state = (current_state + 1) % N;
                    break;
                }
            }
            
            // 出力画像に次の状態を書き込む
            out[y * w + x] = next_state / (double)(N - 1);
        }
    }
    
    // ステップ数分繰り返す
    for (int step = 0; step < steps; step++) {
        double* temp = (double*)malloc(h * w * sizeof(double));
        fs2_apply(out, h, w, a, b, temp);
        for (int i = 0; i < h * w; i++) {
            out[i] = temp[i];
        }
        free(temp);
    }
}
