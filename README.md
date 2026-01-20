# 🧹 NLP Intelligent Corpus Cleaning Tool

### (NLP 智能语料清洗工具 - Electron 版)

这是一个专为**新闻语料处理**设计的现代化桌面工具。它结合了 **React** 和 **Python**，能够自动将格式混乱的 RTF 新闻文档清洗为结构化的数据。

---

## ✨ 核心功能

* **⚡ 硬件加速**：自动识别你的电脑硬件。
* **NVIDIA 显卡**：开启 CUDA 加速。
* **Mac M1/M2/M3**：开启 Metal (MPS) 加速。
* **普通电脑**：自动切换 CPU 模式，保证能跑。


* **🧠 AI 智能去噪**：内置 DeBERTa AI 模型，自动识别并删除广告、无关链接和图片说明等噪音。
* **📂 批量处理**：一键处理成百上千个文件。
* **📊 可视化**：实时进度条、硬件状态监控、Excel 报表生成。

---

## 🛠️ 第一步：环境准备 (必读)

在运行本软件之前，你的电脑需要安装以下三个基础软件。如果已安装请跳过。

### 1. 安装 Node.js (用于运行界面)

* **下载地址**: [Node.js 官网](https://nodejs.org/)
* **版本建议**: 下载 **LTS (长期支持版)**，例如 v18 或 v20。
* **检查方法**: 打开终端(CMD)，输入 `node -v`，如果不报错即为成功。

### 2. 安装 Python (用于运行 AI)

* **下载地址**: [Python 官网](https://www.python.org/downloads/)
* **版本建议**: **Python 3.8 ~ 3.11** (建议 3.10)。
* **注意**: 安装时务必勾选 **"Add Python to PATH"**。

### 3. 安装 Git (用于下载代码)

* **下载地址**: [Git 官网](https://git-scm.com/)
* **说明**: 一路点击 Next 安装即可。

---

## 📥 第二步：下载与安装

### 1. 下载项目代码

找一个你存放代码的文件夹（例如 D盘），新建文件夹，在空白处右键 -> "Open Git Bash Here" 或者打开终端：

```bash
git clone https://github.com/你的用户名/SHOU-NLP-News-Cleaning-Pipeline.git
cd SHOU-NLP-News-Cleaning-Pipeline
```

### 2. 安装后端依赖 (Python)

在项目**根目录**下，运行以下命令来安装 AI 引擎需要的库：

```bash
pip install -r requirements.txt
```

> **⚠️ 关于显卡加速 (CUDA)**：
> 上面的命令默认安装 CPU 版 PyTorch。如果你有 NVIDIA 显卡并想跑得更快，请去 [PyTorch 官网](https://pytorch.org/get-started/locally/) 复制对应的安装命令覆盖安装。

### 3. 安装前端依赖 (Node.js)

进入前端文件夹并安装依赖：

```bash
cd css-interface
npm install
```

---

## 📥 第三步：下载 AI 模型 (关键！)

为了减小软件体积，核心模型文件不包含在代码中，**你需要手动下载并放入指定位置**。

### 1. 下载模型文件

请从以下任一地址下载模型包：

* **百度网盘**: [点击这里下载] (提取码: `vx86`) *(请填入你真实的链接)*
* **HuggingFace**: [点击这里下载] *(如果你上传了的话)*

### 2. 放置模型

下载并解压后，请确保你的**项目根目录**下有一个名为 `models` 的文件夹，结构如下：

```text
SHOU-NLP-News-Cleaning-Pipeline/
├── api.py                 # [后端] Python 入口
├── pipeline_modules.py    # [后端] AI 核心逻辑
├── requirements.txt       # [后端] 依赖列表
├── models/                # [模型文件夹]
│   ├── noise-cleaner-deberta-v2/
│   │   └── final/         # <--- 注意：模型文件必须在这里面！
│   │       ├── config.json
│   │       ├── model.safetensors
│   │       └── ...
│   └── all-MiniLM-L6-v2/
│       └── ...
└── css-interface/         # [前端] 界面源码

```

DeBERTa 模型:

路径: models/noise-cleaner-deberta-v2/final/

确保 config.json 和 model.safetensors 在 final 文件夹里面。

MiniLM 模型:

路径: models/all-MiniLM-L6-v2/

---

## 🚀 第四步：启动软件

一切准备就绪！现在启动它。

1. **打开终端**，确保你位于 `css-interface` 文件夹内：
```bash
# 如果你还在根目录
cd css-interface
```


2. **运行启动命令**：
```bash
npm run dev
```


3. **等待启动**：
* 此时会弹出一个软件窗口。
* **注意**：左下角的硬件卡片可能会显示 *"Checking Hardware..."* 或 *"Loading..."* 约 **5~10秒**。这是 Python 正在后台加载 AI 引擎，**请耐心等待**，直到它显示出你的显卡型号（如 RTX 4070 或 CPU Mode）。


---

## 📖 软件功能页面详解 (User Manual)

本软件主要包含三个核心交互区域，分别对应**配置**、**运行**和**监控**。

### 1. 🏠 主控面板 (Dashboard)

这是软件启动后的默认页面，是操作台。

**👀 你会看到什么：**

* **⚡ 硬件状态卡片 (Hardware Status)**：
* 位于左下角/侧边栏。
* **绿色 (CUDA Accelerated)**：说明你的电脑有 NVIDIA 显卡，AI 运行速度会很快。
* **紫色 (Apple Metal)**：说明你是 Mac 电脑，正在使用 M 芯片加速。
* **灰色 (CPU Mode)**：说明正在使用处理器运行，速度稍慢但也能用。


* **🧠 模型状态 (Core Engine)**：
* 显示 `DeBERTa Ready` 表示 AI 模型已加载完毕。
* 如果显示 `Loading...`，请耐心等待几秒。


* **📂 路径选择器**：
* **Source Directory**: 选择存放原始 RTF 新闻稿的文件夹。
* **Destination Directory**: 选择一个空文件夹，用来存放清洗好的 TXT 和 Excel 
* **Destination Directory**: **推荐勾选Auto Set /Outout**，会自动在Source Directory下创建output目录。



**👉 你需要做什么：**

1. 点击 `Source Directory` 选择你的语料文件夹。
2. 点击 `Destination Directory` 选择保存结果的位置。
3. 点击最下方的 **Initialize Run (▶)** 按钮开始任务。

---

### 2. 🛡️ 语义规则编辑器 (Semantic Rules Editor)

*入口：位于侧边栏的“Dashboard”下方*

你可以在这里设置用于筛选文章话题的规则。

**👀 你会看到什么：**

* **✅ Positive Rules (保留规则)**：
* 这里列出的关键词/句子，告诉 AI：“只要文章里出现这些话题，就**一定保留**，不要删错了。”
* *例子：Diplomacy, Bilateral relations, Government official visits.*


* **❌ Negative Rules (剔除规则)**：
* 这里列出的关键词，告诉 AI：“这些通常是垃圾广告或无关内容，**优先删除**。”
* *例子：Stock market fluctuations, Holiday packages, Celebrity gossip.*



**👉 你需要做什么：**

* 如果你发现 AI 把某些重要的新闻误删了，在 **Positive** 里加一个关键词。
* 如果你发现清洗结果里还残留着广告，在 **Negative** 里加一个关键词。
* 修改完后，记得点击 **Save Config**。

---


### 3. 🔬 审查实验室 (Review Lab)

*入口：任务完成后点击 "Review Lab" 按钮*

在这里，你可以直观地看到 AI 到底对原始文档做了什么——它删了哪里？保留了哪里？这是确保数据质量最关键的一步。

**👀 你会看到什么 (颜色解码)：**

界面中文本会以不同的背景色显示，它们代表不同的含义：

* 🔴 **红色高亮 (AI Removed)**：
* **含义**：这是被 AI 模型判定为“噪音”并**删除**的内容。
* **通常包括**：广告、图片说明、无关的推荐链接、作者的社交媒体账号等。
* **你需要检查**：快速扫视红色区域，确认**没有**误删重要的新闻正文。


* ⚪ **灰色高亮 (Rule Removed)**：
* **含义**：这是被正则表达式（规则）**切除**的结构化信息。
* **通常包括**：文档头部的版权声明、日期、来源，以及底部的无关页脚。
* **状态**：这些信息虽然从正文中移除了，但通常会被提取到 Excel 的元数据列中。


* ⚫ **普通黑字 (Kept)**：
* **含义**：这是最终被**保留**下来的纯净新闻正文。
* **结果**：这部分内容会进入最终的 `.txt` 文件。



**👉 你需要做什么：**

1. **手动修改**： AI 并不是完美的。在浏览时，如果你发现 AI 犯了错，请立即纠正。
2. **标记完成与进度**：当你确认一篇文章没问题后，务必点击右上角的 "Mark Checked" 按钮。
此时文件会被标记为绿色（已完成）
3. **目录进度**: 左侧文件列表会显示每个子文件夹的完成度（例如 Global_News: 15/50）。请确保你负责的文件夹进度达到 100%。


---


### 4. 📊 输出结果 (The Output)

任务完成后，打开你设置的 **Output Folder**，你会得到以下成果：

**📁 结果文件结构：**

1. **📄 Cleaned TXT Files**:
* 每个原始 RTF 对应一个 TXT。
* 内容已去除广告，并自动标记了 `<TITLE>`, `<DATE>`, `<BODY>` 等标签。


2. **📈 Excel 汇总表 (Summary.xlsx)**:
* 包含所有文章的元数据（标题、日期、来源）汇总。
* 在Mark Checked之后，Checked会变成YES。


3. **🔍 差异对比文件 (diff_check.json)**:
* **高级功能**：实现Review Lab中不同文本的颜色标记。



---



## ❓ 常见问题 (FAQ)

**Q: 打开软件后一直显示 "Loading path..." 或者是灰色的？**
A: 请给它一点时间（10-15秒）。如果 1分钟还没反应，请查看刚才运行 `npm run dev` 的那个黑色终端窗口，看看有没有报错信息。

**Q: 报错 `ModuleNotFoundError`？**
A: 这说明你忘记运行 `pip install -r requirements.txt` 了，或者安装错位置了。请回到第二步。

**Q: 为什么第一次处理速度很慢？**
A: 模型需要“预热”。第一次点击 Start 后，AI 需要加载到内存，之后的处理速度会加快。

---

## 📁 项目结构说明 (供开发者参考)

```text
Project_Root/
├── api.py                 # [后端] Python 入口，负责与前端通信
├── pipeline_modules.py    # [后端] AI 处理核心逻辑
├── requirements.txt       # [后端] Python 依赖列表
├── models/                # [模型] 存放下载的大模型文件
└── css-interface/         # [前端] React + Electron 界面源码
    ├── src/               # React 源代码
    ├── electron/          # Electron 主进程代码
    └── package.json       # 前端配置

```

---
<div align="center">

![Last Updated](https://img.shields.io/github/last-commit/sc128307/SHOU-NLP-News-Cleaning-Pipeline?label=Last%20Updated&style=flat-square&color=5D5FEF)
</div>
