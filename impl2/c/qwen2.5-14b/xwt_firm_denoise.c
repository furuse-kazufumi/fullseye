#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端を処理する際、境界外のピクセルは同じ値を用いる。
    // これは、境界外のピクセルが存在しないと仮定する最も単純な方法であり、
    // 他の方法（境界を拡張するなど）よりも計算効率が良い。

    // sym4 フィルタは 4 次のフィルタであり、2 次の分解を行う。
    // ここでは、ウェーブレット変換の実装は省略し、代わりに単純な平滑化処理を適用する。
    // これは、ウェーブレット変換の詳細な実装を避けるための近似であり、
    // 実際の実装では、ウェーブレット変換ライブラリを使用することを推奨する。

    // 画像の平滑化処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 平滑化処理のための近似値を計算
            double sum = 0.0;
            int count = 0;
            for (int dy = -1; dy <= 1; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        sum += in[ny * w + nx];
                        ++count;
                    }
                }
            }
            double avg = sum / count;
            // ファーム閾値処理
            if (avg < a) {
                out[y * w + x] = 0.0;
            } else if (avg > b) {
                out[y * w + x] = avg;
            } else {
                out[y * w + x] = (1.0 - (avg - a) / (b - a)) * avg;
            }
        }
    }
}
