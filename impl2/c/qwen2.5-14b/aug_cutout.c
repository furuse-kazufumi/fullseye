#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の最小サイズを計算
    int min_dim = (h < w) ? h : w;
    int patch_size = max(1, (int)(a * min_dim)); // パッチのサイズを計算

    // パッチの位置を決定
    int patch_x = rand() % (w - patch_size + 1);
    int patch_y = rand() % (h - patch_size + 1);

    // パッチの値を決定
    double fill_value = (b <= 0.5) ? 0.0 : 0.5;

    // 出力画像を入力画像と同じにする
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // パッチを適用
    for (int y = patch_y; y < patch_y + patch_size; y++) {
        for (int x = patch_x; x < patch_x + patch_size; x++) {
            out[y * w + x] = fill_value;
        }
    }
}

// max 関数の定義
int max(int a, int b) {
    return (a > b) ? a : b;
}
