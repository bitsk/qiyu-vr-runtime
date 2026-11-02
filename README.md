# qiyu-vr-runtime

固定上游 Monado 的 A081 SteamVR 下游补丁与图形依赖。


构建入口和依赖见下方；工程 Wiki/Blog 与跨仓库规划集中在 [qiyu-docs](https://github.com/bitsk/qiyu-docs)。

## 构建

`python3 tools/build.py --monado-repo /path/to/upstream/monado --output /new/build --cmake-option=-DCMAKE_TOOLCHAIN_FILE=/path/to/toolchain.cmake`

相邻检出 qiyu-head-tracking / qiyu-controller-tracking，构建时复制其固定版本协议头到临时源码树；协议头只有一个维护源。`--prepare-only` 导出并核对完整下游源文件；正常构建需要 CMake、Ninja、arm64 工具链、Eigen3、glslang 和 libudev 开发依赖。上游固定提交、补丁及源摘要见 upstream.json。`graphics/` 保留 Mesa/Turnip 补丁与历史配方，不会自动替换系统图形库。当前构建目标为已用的 Linux SteamVR provider，未声称补齐所有 OpenXR/compositor 后端。
