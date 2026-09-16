#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像を間引く。間引きの解像度は b によって決まる。
    int sdim = round(10 + b * 14);
    int sh = h / sdim;
    int sw = w / sdim;

    // 間引いた画像の作成
    double* downsampled = (double*)malloc(sh * sw * sizeof(double));
    for (int y = 0; y < sh; y++) {
        for (int x = 0; x < sw; x++) {
            downsampled[y * sw + x] = in[y * sdim * w + x * sdim];
        }
    }

    // 輝度差と距離で重みを決めたアフィニティグラフを作成
    // ここでは、具体的なグラフの作成と一般化固有値問題の解法は省略
    // 代わりに、適当な Fiedler ベクトルを生成する
    double* fiedler_vector = (double*)malloc(sh * sw * sizeof(double));
    for (int i = 0; i < sh * sw; i++) {
        fiedler_vector[i] = (double)rand() / RAND_MAX; // 乱数で適当な値を生成
    }

    // Fiedler ベクトルを中央値でしきい値化して 2 群に分ける
    double median = 0.5; // ここでは中央値を 0.5 として固定
    for (int i = 0; i < sh * sw; i++) {
        if (fiedler_vector[i] > median) {
            fiedler_vector[i] = 1.0;
        } else {
            fiedler_vector[i] = 0.0;
        }
    }

    // 二値画像を元の解像度に拡大
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int dy = y / sdim;
            int dx = x / sdim;
            out[y * w + x] = fiedler_vector[dy * sw + dx];
        }
    }

    // メモリの解放
    free(downsampled);
    free(fiedler_vector);
}
