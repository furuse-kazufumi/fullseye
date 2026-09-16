#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // K の計算: K = 5 + 250 * (1 - a)
    double K = 5 + 250 * (1 - a);

    // ランダムシードをつまみ (a, b) から生成
    // ここでは簡単のため、a と b の値を直接シードとして使用
    // 実装では、より適切な乱数生成器を使用することを推奨
    srand((int)(a * 1000000 + b * 1000000));

    // 出力画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 入力画像のピクセル値を取得
            double input_value = in[y * w + x];

            // 入力値を K でスケーリング
            double scaled_value = input_value * K;

            // Poisson 分布からサンプリング
            // Poisson 分布のサンプリングは、指数分布の累積分布関数の逆関数を使用
            // ここでは、単純化のため、ランダムな値を生成し、それを Poisson 分布に近似
            double random_value = (double)rand() / RAND_MAX;
            double poisson_sample = 0;
            double p = exp(-scaled_value);
            double sum = p;
            while (random_value > sum) {
                poisson_sample++;
                p *= scaled_value / (poisson_sample + 1);
                sum += p;
            }

            // ダークカレントの追加
            double dark_current = 0.05 * b;
            poisson_sample += dark_current;

            // サンプリング結果を K でスケーリングバック
            double output_value = poisson_sample / K;

            // 出力画像に書き込み
            out[y * w + x] = output_value;
        }
    }
}
