#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用
    (void)a;
    (void)b;

    // 出力画像のサイズ
    int size = h * w;

    // 逆フーリエ変換のためのテンポラリ配列
    double* temp = (double*)malloc(size * sizeof(double) * 2); // 実部と虚部のための2倍のサイズ
    if (temp == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // 入力画像を複素数配列として扱う
    for (int i = 0; i < size; i++) {
        temp[i * 2] = in[i]; // 実部
        temp[i * 2 + 1] = 0.0; // 虚部
    }

    // 逆フーリエ変換 (ここでは手動で実装)
    // 実際の実装では FFTW などのライブラリを使用することを推奨
    // 以下は逆フーリエ変換の擬似的な実装例
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double real = 0.0;
            for (int u = 0; u < h; u++) {
                for (int v = 0; v < w; v++) {
                    double angle = -2 * M_PI * (u * x / (double)w + v * y / (double)h);
                    real += temp[u * w * 2 + v] * cos(angle) - temp[u * w * 2 + v + 1] * sin(angle);
                }
            }
            out[y * w + x] = real / (h * w); // 正規化
        }
    }

    // 最大値で正規化
    double max_val = 0.0;
    for (int i = 0; i < size; i++) {
        if (out[i] > max_val) {
            max_val = out[i];
        }
    }
    if (max_val > 0.0) {
        for (int i = 0; i < size; i++) {
            out[i] /= max_val;
        }
    }

    // メモリ解放
    free(temp);
}
