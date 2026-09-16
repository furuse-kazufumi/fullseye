#include <math.h>
#include <stdlib.h>
#include <string.h>

// 定数定義
#define THRESHOLD 0.5
#define MAX_RULES 256

// ルールテーブルの定義
const int _ELEMENTARY_RULES[MAX_RULES] = {
    // ここにルールテーブルを定義します。実際には256個の整数が必要です。
    // ここでは例として一部を示します。
    0, 170, 190, 204, 205, 210, 218, 224, 225, 230, 238, 240, 241, 242, 243, 244, 245,
    // 以下略
};

// 初期状態の生成関数
void generate_initial_state(const double* in, int h, int w, double b, int* state) {
    int seed_count = (int)(b * w / 2);
    int seed_positions[seed_count];
    int seed_index = 0;

    // 初期状態の生成
    for (int x = 0; x < w; x++) {
        if (x == w / 2) {
            state[x] = 1; // 中央のシード
        } else {
            state[x] = (in[x] > THRESHOLD) ? 1 : 0;
        }
    }

    // 追加のシードの生成
    if (seed_count > 0) {
        int interval = w / (2 * seed_count);
        for (int i = 0; i < seed_count; i++) {
            seed_positions[i] = i * interval;
        }
        for (int i = 0; i < seed_count; i++) {
            state[seed_positions[i]] = 1;
            state[w - 1 - seed_positions[i]] = 1;
        }
    }
}

// 1世代のシミュレーション
void simulate_generation(int* current_state, int* next_state, int w, int rule) {
    for (int x = 0; x < w; x++) {
        int left = (x == 0) ? current_state[w - 1] : current_state[x - 1];
        int center = current_state[x];
        int right = (x == w - 1) ? current_state[0] : current_state[x + 1];
        int neighborhood = (left << 1) | center | (right >> 1);
        next_state[x] = (_ELEMENTARY_RULES[rule] >> neighborhood) & 1;
    }
}

// fs2_apply 関数
void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int* state = (int*)malloc(w * sizeof(int));
    int* next_state = (int*)malloc(w * sizeof(int));

    // 初期状態の生成
    generate_initial_state(in, h, w, b, state);

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // ルールの選択
    int rule = (int)(a * MAX_RULES);

    // 世代のシミュレーション
    for (int y = 0; y < h; y++) {
        // 現在の状態を出力画像にコピー
        for (int x = 0; x < w; x++) {
            out[y * w + x] = state[x];
        }

        // 次の世代の状態を計算
        simulate_generation(state, next_state, w, rule);

        // 次の世代の状態を現在の状態にコピー
        for (int x = 0; x < w; x++) {
            state[x] = next_state[x];
        }
    }

    // メモリの解放
    free(state);
    free(next_state);
}
