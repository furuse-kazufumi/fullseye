#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 乱数生成器のシードを a から決定的に導出
    unsigned int seed = (unsigned int)(a * 997) + 7;
    // 標準偏差を b から計算
    double std_dev = 0.02 + 0.2 * b;

    // 乱数生成器の初期化
    unsigned int state[624];
    unsigned int *next = state;
    unsigned int left = 624;
    unsigned int y = 0;
    unsigned int mag01[2] = {0x9908b0df, 0x9908b0df};
    unsigned int *mt = state;
    unsigned int mti = 624;

    // メルセンヌツイスタの初期化
    for (int i = 0; i < 624; i++) {
        state[i] = (seed >> (32 - (i % 32))) | (seed << ((i % 32)));
        seed = state[i];
    }
    state[0] |= 0x80000000; // MSB set to 1

    // メルセンヌツイスタの乱数生成関数
    unsigned int genrand_int32(void) {
        unsigned int y;
        if (mti >= 624) {
            int kk;
            for (kk = 0; kk < 227; kk++) {
                y = (mt[kk] & 0x80000000) | (mt[kk + 1] & 0x7fffffff);
                mt[kk] = mt[kk + 397] ^ (y >> 1) ^ mag01[y & 0x1];
            }
            for (; kk < 623; kk++) {
                y = (mt[kk] & 0x80000000) | (mt[kk + 1] & 0x7fffffff);
                mt[kk] = mt[kk + 397] ^ (y >> 1) ^ mag01[y & 0x1];
            }
            y = (mt[623] & 0x80000000) | (mt[0] & 0x7fffffff);
            mt[623] = mt[396] ^ (y >> 1) ^ mag01[y & 0x1];
            mti = 0;
        }
        y = mt[mti++];
        y ^= (y >> 11);
        y ^= (y << 7) & 0x9d2c5680;
        y ^= (y << 15) & 0xefc60000;
        y ^= (y >> 18);
        return y;
    }

    // 画像の各ピクセルに対してノイズを加える
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 乱数を生成
            double noise = (double)genrand_int32() / (double)0xffffffff;
            noise = (noise * 2.0 - 1.0) * std_dev; // [-1, 1] -> [-std_dev, std_dev]
            // ノイズを加える
            double value = in[y * w + x] + noise;
            // 値域を [0, 1] にクリップ
            out[y * w + x] = value < 0.0 ? 0.0 : (value > 1.0 ? 1.0 : value);
        }
    }
}
