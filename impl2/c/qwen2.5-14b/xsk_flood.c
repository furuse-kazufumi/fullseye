#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double tolerance = 0.05 + a * 0.30; // a が 0.0 から 1.0 の範囲で tolerance を 0.05 から 0.35 に変化させる
    const double center_x = w / 2.0;
    const double center_y = h / 2.0;
    const double center_value = in[(int)center_y * w + (int)center_x];

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // Flood fill 関数の呼び出し
    flood_fill(in, h, w, center_x, center_y, center_value, tolerance, out);

    // 二値化処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = (out[y * w + x] > 0.5) ? 1.0 : 0.0;
        }
    }
}

void flood_fill(const double* in, int h, int w, double cx, double cy, double cv, double tol, double* out) {
    // ここでは flood fill アルゴリズムを実装します。
    // 画像の端を処理する際は、端の画素を無視するようにします。
    // これは、端の画素が flood fill の範囲外である可能性があるためです。

    // ここに flood fill の実装を追加します。
    // 以下は flood fill の基本的なフレームワークです。

    // スタックを使用して flood fill を実装
    int stack[2 * h * w];
    int stack_top = 0;

    // スタート位置をスタックにプッシュ
    stack[stack_top++] = (int)cy * w + (int)cx;

    while (stack_top > 0) {
        int idx = stack[--stack_top];
        int y = idx / w;
        int x = idx % w;

        // 既に処理済みの場合はスキップ
        if (out[idx] > 0.0) continue;

        // 画素値を取得
        double value = in[idx];

        // 許容範囲内かどうかをチェック
        if (fabs(value - cv) > tol) continue;

        // 出力画像に設定
        out[idx] = 1.0;

        // 4方向に隣接する画素をスタックにプッシュ
        if (x > 0) stack[stack_top++] = idx - 1; // 左
        if (x < w - 1) stack[stack_top++] = idx + 1; // 右
        if (y > 0) stack[stack_top++] = idx - w; // 上
        if (y < h - 1) stack[stack_top++] = idx + w; // 下
    }
}
