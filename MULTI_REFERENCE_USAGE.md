# FaceFusion 多人换脸命令

## 两种模式对比

### Many模式 - 所有人换同一张脸
```bash
python facefusion.py headless-run \
  --face-selector-mode many \
  --source-paths ./face_1_update.jpg \
  --target-path ./test.mp4 \
  --output-path ./output.mp4 \
  --processors face_swapper
```
**注意**: Many模式直接使用 `--source-paths` 参数，将视频中所有人脸替换为同一张脸

### Reference模式 - 不同人换不同脸
```bash
python facefusion.py headless-run \
  --face-selector-mode reference \
  --face-mappings-file mapping.json \
  --target-path ./test.mp4 \
  --output-path ./output.mp4 \
  --processors face_swapper
```
**注意**: Reference模式使用 `--face-mappings-file` 参数，通过配置文件精确控制每个人的替换

---

## Reference模式配置示例

### 单人换脸 (1对1)
```bash
python facefusion.py headless-run \
  --face-selector-mode reference \
  --face-mappings-file mapping_single.json \
  --target-path ./test.mp4 \
  --output-path ./output.mp4 \
  --processors face_swapper
```


### 双人换脸 (2对2)
```bash
python facefusion.py headless-run \
  --face-selector-mode reference \
  --face-mappings-file mapping_dual.json \
  --target-path ./test.mp4 \
  --output-path ./output.mp4 \
  --processors face_swapper
```


### 三人换脸 (3对3)
```bash
python facefusion.py headless-run \
  --face-selector-mode reference \
  --face-mappings-file mapping_triple.json \
  --target-path ./test.mp4 \
  --output-path ./output.mp4 \
  --processors face_swapper
```


