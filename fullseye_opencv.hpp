// Optional OpenCV adapter / OpenCV 任意アダプタ。
#pragma once

#include "fullseye.hpp"

// Define FULLSEYE_WITH_OPENCV only in a target that links OpenCV.  Keeping this
// separate means ordinary Fullseye C++ users do not acquire an OpenCV header or
// ABI dependency. / OpenCV をリンクする target だけで定義する。分離したため、
// 通常の Fullseye C++ 利用者に OpenCV のヘッダ・ABI 依存は増えない。
#ifdef FULLSEYE_WITH_OPENCV
#  include <opencv2/core/mat.hpp>

namespace fullseye {

inline Image image_from_mat(const cv::Mat &mat,
                            BufferOwnership ownership = BufferOwnership::borrow) {
    if (mat.empty() || mat.type() != CV_64FC1 || !mat.isContinuous()) {
        throw std::invalid_argument(
            "image_from_mat requires a non-empty, continuous CV_64FC1 cv::Mat");
    }
    return Image::from_buffer(mat.ptr<double>(), mat.rows, mat.cols, ownership);
}

}  // namespace fullseye
#endif
