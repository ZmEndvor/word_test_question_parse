# 图像处理，去除杂质
import cv2
import pytesseract
from skimage.filters import threshold_local
from PIL import Image
import numpy as np


def _show_img(img, msg):
    print(msg)
    cv2.imshow(msg, img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def img_proc(image: Image):
    """
    图像预处理

    去噪、二值化
    :param img:
    :return:
    """
    # 转为灰度图像，去燥(高斯模糊)，查找轮廓
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _show_img(gray, '灰度')
    #gray = cv2.GaussianBlur(gray, (3, 3), 0)
    gray = cv2.medianBlur(gray, 3)
    #gray=cv2.blur(gray, (3,3))
    #_show_img(gray, '平滑去噪')

    #kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], np.float32)  # 锐化
    #gray = cv2.filter2D(gray, -1, kernel=kernel)

    #_show_img(gray, '锐化')

    T = threshold_local(gray,11, offset=20, method="gaussian")
    # _show_img(T, 'threshold-local')
    warped = (gray > T).astype("uint8") * 255
    _show_img(warped, '二值化')

    return warped


if __name__ == '__main__':
    """
    目前测试效果不佳，原始扫描件比较清晰。效果已经不错了
    """
    img = cv2.imread("scan.png")
    result = pytesseract.image_to_string("scan.png", lang="chi_sim+eng+equ")
    print(result)
    gray = img_proc(img)
    color_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    cv2.imwrite("temp2.png", color_img)

    result = pytesseract.image_to_string("temp2.png", lang="chi_sim+eng+equ")
    print(result)
