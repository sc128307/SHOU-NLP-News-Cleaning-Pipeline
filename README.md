
# NLP Intelligent Corpus Cleaning Tool (NLP 智能语料清洗工具)

![Python](https://img.shields.io/badge/Python-3.9%2B-blue) ![PyTorch](https://img.shields.io/badge/PyTorch-Enabled-red) ![Transformers](https://img.shields.io/badge/HuggingFace-Transformers-yellow)

这是一个专为新闻语料处理设计的自动化清洗管线。它能够将原始的、格式混乱的 **RTF 文档** 批量转换为结构化清晰、内容纯净的 **TXT 和 Excel 数据**。

该工具采用 **“规则 + AI” 混合架构**，结合了正则表达式的精准结构提取能力和 DistilBERT 模型的语义理解能力，有效去除正文中的广告、图片说明、无关链接及作者简介等噪音。

## ✨ 主要功能 (Key Features)

* **🚀 全自动批处理**：支持递归扫描文件夹，一键处理成百上千个 RTF 文件。
* **🧠 AI 智能去噪**：内置微调过的 DistilBERT 分类模型，能精准识别并剔除正文夹杂的广告、图片描述和无关引导语。
* **📐 精准结构提取**：利用 Regex 规则完美提取 `TITLE` (标题), `DATE` (日期), `SOURCE` (来源) 和 `BODY` (正文)。
* **🖥️ 图形化界面 (GUI)**：提供现代化的操作界面，非技术人员也能轻松使用。
* **⚙️ 硬件自适应**：自动检测系统硬件。有 NVIDIA 显卡则使用 CUDA 加速，无显卡自动切换至 CPU 模式（组员无需配置显卡）。
* **📊 进度与日志**：生成 Excel 汇总表，并支持 CSV 增量记录检查进度。
* **🔍 质量验证**：支持生成 Label Studio 格式的差异对比文件（Diff View），用于人工核查清洗效果。

## 📂 项目结构 (Directory Structure)

在使用前，请确保您的目录结构如下所示：

```text
Project_Root/
│
├── news-body-classifier-model/      # [核心] 预训练好的 AI 模型文件夹 (请勿删除!)
│   ├── config.json
│   ├── model.safetensors
│   └── ...
│
├── pipeline_backend.py         # 后端核心逻辑脚本
├── pipeline_gui.py             # 图形界面脚本
├── start_tool.bat              # [推荐] Windows 一键启动脚本
│
├── requirements.txt            # 依赖库列表 (可选)
└── README.md                   # 说明文档
````

## 🛠️ 安装指南 (Installation)

### 1\. 环境准备

建议使用 Anaconda 创建一个独立的 Python 环境，以避免冲突。

```bash
# 1. 创建环境 (建议 Python 3.9 或 3.10)
conda create -n nlp-corpus python=3.9

# 2. 激活环境
conda activate nlp-corpus
```

### 2\. 安装依赖

在终端中运行以下命令安装所需的 Python 库：

```bash
# 安装基础依赖
pip install pandas openpyxl striprtf nltk ttkbootstrap

# 安装 AI 相关依赖 (PyTorch 和 Transformers)
# 如果您有 NVIDIA 显卡，建议去 pytorch.org 获取专门的安装命令以启用 GPU 加速
# 如果只有 CPU，直接运行：
pip install torch transformers
```

## 🧠 模型设置 (Model Setup) - 重要！

本工具需要加载 `news-body-classifier-model` 才能工作。您有两种方式获取模型：

### 方法 A：自动下载 (推荐 - Hugging Face)

默认情况下，脚本会自动连接 Hugging Face 服务器下载模型。

  * **优点**：无需任何操作，保持网络通畅即可。
  * **操作**：直接运行工具，无需修改设置。

### 方法 B：手动下载 (备用 - 百度网盘)

如果您的网络无法连接 Hugging Face，请使用此方法。

1.  **下载模型包**：
      * **链接**: `https://pan.baidu.com/s/1mcNLdz9p38ChWeAGs4MSgA?pwd=vx86`
      * **提取码**: `vx86`
2.  **解压**：
      * 将下载的压缩包解压到项目根目录下。
      * 确保文件夹名称为 **`news-body-classifier-model`**。
      * *检查：该文件夹内应包含 `config.json` 和 `model.safetensors` 等文件。*
3.  **配置工具**：
      * 打开工具 GUI。
      * 在 **“3. 模型路径”** 输入框中，点击“浏览”，选择刚刚解压的 `news-body-classifier-model` 文件夹。
      * 或者手动填入路径：`./news-body-classifier-model`。


## 🚀 使用说明 (Usage)

### 方法 A：使用图形界面 (推荐)

1.  **双击运行**项目目录下的 `start_tool.bat` 文件。
2.  在弹出的界面中：
      * **输入目录**：选择包含 `.rtf` 文件的文件夹（支持包含子文件夹）。
      * **输出目录**：选择一个空文件夹，用于存放生成的 `.txt` 和 `.xlsx`。
      * **模型路径**：默认会自动指向 `news-body-classifier-model`，通常无需修改。
3.  点击 **“开始处理”**。
4.  等待进度条完成，结果将自动保存在输出目录中。

### 方法 B：命令行运行 (开发者模式)

如果您希望查看详细的控制台日志，可以在激活环境后运行：

```bash
python pipeline_gui.py
```


## 🧠 技术原理 (Technical Details)

本工具采用 **Hybrid Extraction Strategy (混合提取策略)**：

1.  **RTF 清洗**：使用 `striprtf` 库解析富文本，并辅以自定义正则修复常见的粘连问题（如 `toChina`）。
2.  **结构化提取 (Regex)**：
      * 利用新闻稿固定的排版特征（如 Copyright 行、Document ID 行）进行物理切割，精准分离 Header（元数据）和 Footer（页脚）。
      * 提取 Title, Date, Source。
3.  **正文清洗 (AI Classifier)**：
      * 将正文部分切分为句子。
      * 使用微调后的 **DistilBERT** 模型逐句判断：是 `CONTENT` (保留) 还是 `NOISE` (丢弃)。
      * 辅助规则：利用正则进一步清洗模型可能漏掉的 URL、署名 (Byline) 和图片说明。
4.  **扫尾逻辑**：自动检测并切除文章末尾残留的作者简介 (Bio) 或联系方式。

## 📄 输出格式 (Output)

生成的 `.txt` 文件将采用类似 XML 的标签格式，方便后续进行 LDA 主题模型分析或导入数据库：

```xml
<TITLE>Senate to end POGO probe</TITLE>
<DATE>19 October 2024</DATE>
<SOURCE>The Manila Times</SOURCE>
<BODY>
THE Senate Committee on Women, Children... (此处为清洗后的纯净正文)
...
</BODY>
```

## ❓ 常见问题 (FAQ)

**Q: 启动 `start_tool.bat` 时闪退怎么办？**
A: 请右键点击该文件选择“编辑”，查看是否正确调用了您的 Conda 环境。或者直接打开 Anaconda Prompt，`cd` 到该目录，输入 `start_tool.bat` 运行以查看报错信息。

**Q: 我的电脑没有 NVIDIA 显卡，能用吗？**
A: **可以。** 程序会自动检测硬件。如果没有检测到 GPU，会自动切换到 CPU 模式。虽然速度会比 GPU 慢一些，但完全可用。

**Q: 输出的 Excel 中某些字符显示乱码？**
A: 脚本已内置非法字符清洗功能。如果仍有问题，请确保您的系统支持 UTF-8 编码。


## 🔍 质量验收 (Quality Assurance with Label Studio)

为了确保清洗效果准确无误，本工具支持生成可视化对比文件。您可以使用 **Label Studio** 直观地查看哪些内容被切除了，哪些被保留了。

### 1. 准备工作
确保您已安装并启动 Label Studio：
```bash
pip install label-studio
label-studio start
````

### 2\. 创建验收项目
1.  label-studio完成加载后会自动打开web-ui
1.  或者你可以在浏览器打开 `http://localhost:8080`。
2.  点击 **Create** 创建新项目，命名为 `Diff_Check`。

### 3\. 配置界面 (Labeling Interface)

进入 **Settings** -\> **Labeling Interface** -\> **Code**，删除原有代码，粘贴以下模板：

```xml
<View>
  <View style="position: sticky; top: 0; background: #fff; z-index: 100; padding: 10px; border-bottom: 1px solid #ccc; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    <Header value="清洗效果验收 (Visual Inspection)" size="5"/>
    
    <View style="display: flex; gap: 20px; margin-top: 5px;">
      <Text name="legend_grey" value="⚪ 灰色 = 结构性切除 (Header/Footer)" style="color: #999; font-size: 14px; font-weight: bold;"/>
      <Text name="legend_red" value="🔴 红色 = AI 智能清洗 (Noise)" style="color: red; font-weight: bold; font-size: 14px;"/>
      <Text name="legend_yellow" value="🟡 黄色 = 人工添加 (Missed)" style="color: #d4b106; font-weight: bold; font-size: 14px;"/>
    </View>
  </View>
  
  <Labels name="label" toName="text">
    <Label value="HEADER" background="#e0e0e0"/>
    <Label value="FOOTER" background="#e0e0e0"/>
    <Label value="NOISE" background="#ff4d4f"/>
    
    <Label value="MISSED_NOISE" background="#FFC107" hotkey="m"/>
  </Labels>

  <View style="padding: 30px; font-size: 18px; line-height: 1.6; font-family: 'Roboto', sans-serif;">
    <Text name="text" value="$text"/>
  </View>
</View>
```

*点击 **Save** 保存配置。*

### 4\. 导入数据

1.  点击 **Import**。
2.  选择输出目录下的 `diff_check.json` (通常在 `Output` 文件夹或各个子文件夹中)。

### 5\. 如何验收

进入标注界面后，您会看到以下颜色编码：

  * **⚪ 灰色区域 (顶部/底部)**：表示被**规则**切除的元数据（标题、日期、来源、版权声明、Document ID）。
      * *检查点：正文开头是否被误切？*
  * **🔴 红色区域 (正文中间)**：表示被**AI 模型**判定为垃圾并删除的内容（图片说明、广告、无关链接）。
      * *检查点：是否有红色的正文句子？（误删）*
  * **⚫ 黑色区域**：表示最终保留在 TXT 中的正文内容。
  * **🟡 黄色操作 (可选)**：如果您发现黑色的正文中还残留有垃圾（漏删），请按下快捷键 **`m`** 并框选它。这可以用于后续优化模型。

-----

![Last Commit](https://img.shields.io/github/last-commit/sc128307/SHOU-NLP-News-Cleaning-Pipeline?label=Last%20Updated&style=flat-square&color=blue)
