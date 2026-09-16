#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // パッチの半径を計算
    int patch_radius = (int)(3 + 8 * a);
    int patch_size = 2 * patch_radius + 1;

    // 出力画像の最大値を初期化
    double max_output = 0.0;

    // テンプレートマッチングのループ
    for (int y = patch_radius; y < h - patch_radius; y++) {
        for (int x = patch_radius; x < w - patch_radius; x++) {
            // パッチの中心点
            int center = y * w + x;

            // パッチの合計と平方和を初期化
            double patch_sum = 0.0;
            double patch_sum_sq = 0.0;

            // パッチの各ピクセルに対して
            for (int py = -patch_radius; py <= patch_radius; py++) {
                for (int px = -patch_radius; px <= patch_radius; px++) {
                    int patch_index = (y + py) * w + (x + px);
                    double patch_value = in[patch_index];
                    patch_sum += patch_value;
                    patch_sum_sq += patch_value * patch_value;
                }
            }

            // パッチの平均と分散を計算
            double patch_mean = patch_sum / (patch_size * patch_size);
            double patch_var = patch_sum_sq / (patch_size * patch_size) - patch_mean * patch_mean;

            // パッチの外側のピクセルに対してテンプレートマッチングを実行
            for (int ty = 0; ty < h; ty++) {
                for (int tx = 0; tx < w; tx++) {
                    // テンプレートの合計と平方和を初期化
                    double template_sum = 0.0;
                    double template_sum_sq = 0.0;

                    // テンプレートの各ピクセルに対して
                    for (int py = -patch_radius; py <= patch_radius; py++) {
                        for (int px = -patch_radius; px <= patch_radius; px++) {
                            int template_index = (ty + py) * w + (tx + px);
                            if (template_index >= 0 && template_index < h * w) {
                                double template_value = in[template_index];
                                template_sum += template_value;
                                template_sum_sq += template_value * template_value;
                            }
                        }
                    }

                    // テンプレートの平均と分散を計算
                    double template_mean = template_sum / (patch_size * patch_size);
                    double template_var = template_sum_sq / (patch_size * patch_size) - template_mean * template_mean;

                    // テンプレートとパッチの類似度を計算
                    double similarity = exp(-0.5 * ((template_mean - patch_mean) * (template_mean - patch_mean) / (patch_var + 1e-6)));

                    // 出力画像の最大値を更新
                    if (similarity > max_output) {
                        max_output = similarity;
                    }

                    // 出力画像に類似度を書き込む
                    out[ty * w + tx] = similarity;
                }
            }
        }
    }

    // 出力画像を最大値で正規化
    for (int i = 0; i < h * w; i++) {
        out[i] /= max_output;
    }
}
