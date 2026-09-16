#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像のピクセル数
    int num_pixels = h * w;

    // クラス数を決定
    int num_classes = 3 + (a > 0.5);

    // 各ピクセルのヒストグラムを計算
    double* histogram = (double*)malloc(sizeof(double) * 256);
    for (int i = 0; i < 256; i++) {
        histogram[i] = 0.0;
    }
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int pixel_value = (int)(in[y * w + x] * 255.0);
            histogram[pixel_value]++;
        }
    }

    // しきい値を計算
    double* thresholds = (double*)malloc(sizeof(double) * (num_classes - 1));
    double* class_probabilities = (double*)malloc(sizeof(double) * num_classes);
    double* class_means = (double*)malloc(sizeof(double) * num_classes);
    double* class_variances = (double*)malloc(sizeof(double) * num_classes);
    double* class_weights = (double*)malloc(sizeof(double) * num_classes);
    double* class_variances_sum = (double*)malloc(sizeof(double) * num_classes);

    // 初期化
    for (int i = 0; i < num_classes; i++) {
        class_probabilities[i] = 0.0;
        class_means[i] = 0.0;
        class_variances[i] = 0.0;
        class_weights[i] = 0.0;
        class_variances_sum[i] = 0.0;
    }

    // ヒストグラムからクラスの確率、平均値、分散を計算
    double total_pixels = num_pixels;
    double total_mean = 0.0;
    for (int i = 0; i < 256; i++) {
        total_mean += i * histogram[i];
    }
    total_mean /= total_pixels;

    for (int i = 0; i < 256; i++) {
        class_probabilities[0] += histogram[i];
        class_means[0] += i * histogram[i];
        class_variances[0] += i * i * histogram[i];
        class_weights[0] += histogram[i];
        class_variances_sum[0] += i * i * histogram[i];
    }
    class_means[0] /= class_weights[0];
    class_variances[0] /= class_weights[0];
    class_variances[0] -= class_means[0] * class_means[0];

    for (int i = 1; i < num_classes; i++) {
        class_probabilities[i] = class_probabilities[i - 1];
        class_means[i] = class_means[i - 1];
        class_variances[i] = class_variances[i - 1];
        class_weights[i] = class_weights[i - 1];
        class_variances_sum[i] = class_variances_sum[i - 1];
    }

    // しきい値を決定
    double max_variance = 0.0;
    for (int t = 1; t < 255; t++) {
        double w1 = class_weights[0];
        double w2 = total_pixels - w1;
        double m1 = class_means[0];
        double m2 = total_mean - (w1 / total_pixels) * m1;
        double v1 = class_variances[0];
        double v2 = total_mean * total_mean - (w1 / total_pixels) * m1 * m1 - (w2 / total_pixels) * m2 * m2;
        double between_variance = w1 * w2 * (m1 - m2) * (m1 - m2) / total_pixels;
        double total_variance = w1 * v1 + w2 * v2;
        double within_variance = total_variance - between_variance;
        if (within_variance > max_variance) {
            max_variance = within_variance;
            thresholds[0] = t;
        }
    }

    // しきい値を追加
    for (int i = 1; i < num_classes - 1; i++) {
        double max_variance = 0.0;
        for (int t = (int)thresholds[i - 1] + 1; t < 255; t++) {
            double w1 = class_weights[i];
            double w2 = total_pixels - w1;
            double m1 = class_means[i];
            double m2 = total_mean - (w1 / total_pixels) * m1;
            double v1 = class_variances[i];
            double v2 = total_mean * total_mean - (w1 / total_pixels) * m1 * m1 - (w2 / total_pixels) * m2 * m2;
            double between_variance = w1 * w2 * (m1 - m2) * (m1 - m2) / total_pixels;
            double total_variance = w1 * v1 + w2 * v2;
            double within_variance = total_variance - between_variance;
            if (within_variance > max_variance) {
                max_variance = within_variance;
                thresholds[i] = t;
            }
        }
    }

    // 画像を量子化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int pixel_value = (int)(in[y * w + x] * 255.0);
            int class_index = 0;
            for (int i = 0; i < num_classes - 1; i++) {
                if (pixel_value > thresholds[i]) {
                    class_index = i + 1;
                }
            }
            out[y * w + x] = (double)class_index / (num_classes - 1);
        }
    }

    // メモリを解放
    free(histogram);
    free(thresholds);
    free(class_probabilities);
    free(class_means);
    free(class_variances);
    free(class_weights);
    free(class_variances_sum);
}
