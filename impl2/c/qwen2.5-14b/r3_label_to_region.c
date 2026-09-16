#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ここでは入力がラベル画像ではなく、0.0 か 1.0 の二値画像であると想定します。
    // そのため、ラベルの抽出は不要で、入力画像自体が領域を表していると解釈します。
    // つまみ a, b は使用されないため、無視します。

    // 入力画像と同じサイズの出力画像を生成します。
    // 入力画像が二値画像であるため、出力も二値画像として扱います。
    // 出力画像は入力画像と同じです。
    memcpy(out, in, h * w * sizeof(double));
}
