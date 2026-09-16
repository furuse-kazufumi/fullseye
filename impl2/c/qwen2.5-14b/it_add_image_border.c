void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 根据 a 的值计算边界宽度
    int border_width = 1 + (int)round(a * 6);
    
    // 计算输出图像的尺寸
    int out_h = h + 2 * border_width;
    int out_w = w + 2 * border_width;

    // 边界填充逻辑：使用反射边界填充
    // 反射边界填充的逻辑如下：
    // - 对于顶部边界，使用倒数第二行的值
    // - 对于底部边界，使用倒数第二行的值
    // - 对于左侧边界，使用倒数第二列的值
    // - 对于右侧边界，使用倒数第二列的值
    // 这种方法确保了边界填充的连续性和对称性。

    // 填充输出图像
    for (int y = 0; y < out_h; y++) {
        for (int x = 0; x < out_w; x++) {
            int in_y = y - border_width;
            int in_x = x - border_width;

            // 处理边界情况
            if (in_y < 0) {
                in_y = -in_y - 1;
            } else if (in_y >= h) {
                in_y = 2 * h - in_y - 2;
            }

            if (in_x < 0) {
                in_x = -in_x - 1;
            } else if (in_x >= w) {
                in_x = 2 * w - in_x - 2;
            }

            // 计算输出图像中的索引
            int out_idx = y * out_w + x;
            int in_idx = in_y * w + in_x;

            // 写入输出图像
            out[out_idx] = in[in_idx];
        }
    }
}
