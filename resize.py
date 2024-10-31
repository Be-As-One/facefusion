import cv2

def resize_image(image, width, height):
    # 读取图像
    image = cv2.imread('debugger.jpeg')

    # 检查图像是否成功读取
    if image is None:
        print("Error: Could not read the image.")
    else:
        # 获取原始图像的尺寸
        original_height, original_width = image.shape[:2]

        # 计算新的尺寸 (宽度, 高度)
        new_size = (original_width // 2, original_height // 2)

        # 调整图像大小
        resized_image = cv2.resize(image, new_size)

        # 保存调整大小后的图像
        cv2.imwrite('resized_debugger.jpeg', resized_image)

        print("Image resized to half of the original size and saved successfully.")


        
