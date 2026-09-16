#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const int MAX_K = 6; // 最大クラスタ数
    const int MAX_ITER = 100; // 最大反復回数
    const double EPSILON = 1e-6; // 收敛阈值

    // パラメータ計算
    int k = 2 + (int)round(4 * a); // クラスタ数
    if (k > MAX_K) k = MAX_K; // クラスタ数の上限を設定

    // 入力画像の輝度値を取得
    double* intensity = (double*)malloc(h * w * sizeof(double));
    for (int i = 0; i < h * w; i++) {
        intensity[i] = in[i];
    }

    // 初期重心の設定
    double* centroids = (double*)malloc(k * sizeof(double));
    for (int i = 0; i < k; i++) {
        centroids[i] = (i + 1.0) / (k + 1.0);
    }

    // k-means クラスタリング
    double* labels = (double*)malloc(h * w * sizeof(double));
    double* old_labels = (double*)malloc(h * w * sizeof(double));
    double* cluster_sums = (double*)calloc(k, sizeof(double));
    double* cluster_counts = (double*)calloc(k, sizeof(double));
    double* cluster_means = (double*)malloc(k * sizeof(double));

    for (int iter = 0; iter < MAX_ITER; iter++) {
        // ラベルの更新
        for (int i = 0; i < h * w; i++) {
            double min_dist = INFINITY;
            int best_cluster = -1;
            for (int j = 0; j < k; j++) {
                double dist = pow(intensity[i] - centroids[j], 2);
                if (dist < min_dist) {
                    min_dist = dist;
                    best_cluster = j;
                }
            }
            labels[i] = best_cluster;
        }

        // 重心の更新
        for (int j = 0; j < k; j++) {
            cluster_sums[j] = 0;
            cluster_counts[j] = 0;
        }
        for (int i = 0; i < h * w; i++) {
            int cluster = (int)labels[i];
            cluster_sums[cluster] += intensity[i];
            cluster_counts[cluster]++;
        }
        for (int j = 0; j < k; j++) {
            if (cluster_counts[j] > 0) {
                cluster_means[j] = cluster_sums[j] / cluster_counts[j];
            } else {
                cluster_means[j] = centroids[j];
            }
        }
        for (int j = 0; j < k; j++) {
            centroids[j] = cluster_means[j];
        }

        // 收敛检查
        double max_change = 0;
        for (int i = 0; i < h * w; i++) {
            if (fabs(labels[i] - old_labels[i]) > max_change) {
                max_change = fabs(labels[i] - old_labels[i]);
            }
        }
        if (max_change < EPSILON) {
            break;
        }
        memcpy(old_labels, labels, h * w * sizeof(double));
    }

    // 最も明るいクラスタの識別
    double max_mean = -INFINITY;
    int best_cluster = -1;
    for (int j = 0; j < k; j++) {
        if (cluster_means[j] > max_mean) {
            max_mean = cluster_means[j];
            best_cluster = j;
        }
    }

    // 出力画像の生成
    for (int i = 0; i < h * w; i++) {
        out[i] = (labels[i] == best_cluster) ? 1.0 : 0.0;
    }

    // メモリの解放
    free(intensity);
    free(centroids);
    free(labels);
    free(old_labels);
    free(cluster_sums);
    free(cluster_counts);
    free(cluster_means);
}
