#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 端の処理: 入力画像の端を重複させずに折り返す
    // これは OpenCV の BORDER_REFLECT_101 に相当する。
    // 例: d c b | a b c d (| は境界)
    // 画像の端を折り返すための補助関数
    int get_reflected_index(int x, int w) {
        if (x < 0) return -x - 1;
        if (x >= w) return w * 2 - x - 1;
        return x;
    }

    // カーネルサイズを計算
    int k = 3 + 2 * (int)(a * 3);
    int k_half = k / 2;

    // 出力画像の各ピクセルに対してカーネルを適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;
            for (int ky = -k_half; ky <= k_half; ky++) {
                for (int kx = -k_half; kx <= k_half; kx++) {
                    int nx = get_reflected_index(x + kx, w);
                    int ny = get_reflected_index(y + ky, h);
                    sum += in[ny * w + nx];
                    count++;
                }
            }
            out[y * w + x] = sum / count;
        }
    }
}
