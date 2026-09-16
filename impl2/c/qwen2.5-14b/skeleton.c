#include <math.h>
#include <stdlib.h>
#include <string.h>

// 定義: 画像の外側は背景(0)とみなす
#define BACKGROUND 0

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の外側を背景とみなすための境界を設定
    // 画像の外側は常に BACKGROUND とみなす
    // 画像の内部は in から読み込む

    // 出力画像の初期化
    memset(out, BACKGROUND, h * w * sizeof(double));

    // 骨格化アルゴリズムの実装
    // ここでは、skeletonize アルゴリズムの基本的なステップを簡略化して実装する
    // 実際の実装では、skimage.morphology.skeletonize のようなライブラリを使用する

    // 画像の各画素について処理
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            // 画素 (x, y) の値を取得
            double pixel_value = in[y * w + x];

            // 画素が領域に属する場合 (pixel_value == 1.0)
            if (pixel_value == 1.0) {
                // 画素の 8 邻接画素の値を取得
                double neighbors[8];
                neighbors[0] = in[(y - 1) * w + (x - 1)];
                neighbors[1] = in[(y - 1) * w + x];
                neighbors[2] = in[(y - 1) * w + (x + 1)];
                neighbors[3] = in[y * w + (x - 1)];
                neighbors[4] = in[y * w + (x + 1)];
                neighbors[5] = in[(y + 1) * w + (x - 1)];
                neighbors[6] = in[(y + 1) * w + x];
                neighbors[7] = in[(y + 1) * w + (x + 1)];

                // 骨格化の条件を満たす場合、出力画像に 1.0 を設定
                // ここでは、単純な条件を設定しているが、実際の骨格化アルゴリズムでは複雑な条件を満たす必要がある
                if (pixel_value == 1.0 && count_neighbors(neighbors) > 1) {
                    out[y * w + x] = 1.0;
                }
            }
        }
    }
}

// 8 邻接画素のうち、1.0 の数をカウントする関数
int count_neighbors(const double* neighbors) {
    int count = 0;
    for (int i = 0; i < 8; i++) {
        if (neighbors[i] == 1.0) {
            count++;
        }
    }
    return count;
}
