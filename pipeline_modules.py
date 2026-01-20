import os
import re
import json
import pandas as pd
import nltk
import torch
import transformers
import unicodedata
import numpy as np
import platform
import psutil
import gc
from striprtf.striprtf import rtf_to_text
from transformers import AutoTokenizer, AutoModelForTokenClassification
from sentence_transformers import SentenceTransformer, util

transformers.logging.set_verbosity_error()

# --- 依赖检查 ---
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)


# ==================================================
# 工具类: 设备管理
# ==================================================
class DeviceManager:
    @staticmethod
    def get_optimal_device():
        """自动检测最佳运行设备: cuda, mps, 或 cpu"""
        device = "cpu"
        info = {"type": "cpu", "vram": 0, "desc": "Standard Processing Unit"}

        # A. 检测 NVIDIA GPU
        if torch.cuda.is_available():
            device = "cuda"
            try:
                device_name = torch.cuda.get_device_name(0)
                vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
                info = {
                    "type": "cuda",
                    "vram": round(vram_gb, 2),
                    "desc": device_name,
                }
            except:
                info["desc"] = "NVIDIA GPU (Unknown)"

        # B. 检测 Apple Silicon (M1/M2/M3)
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = "mps"
            # 获取系统内存作为参考
            total_mem = psutil.virtual_memory().total / 1024**3
            info = {
                "type": "mps",
                "vram": round(total_mem, 1),
                "desc": "Apple Silicon (Metal)",
            }

        return device, info

    @staticmethod
    def get_model_kwargs(device):
        """根据设备返回模型加载参数"""
        kwargs = {}
        if device == "cuda":
            # 显存够的话可以用 float16 加速
            kwargs = {"torch_dtype": torch.float16}
        elif device == "mps":
            # Mac 目前建议使用 float32 保证兼容性，或者尝试 float16
            kwargs = {"torch_dtype": torch.float32}
        else:
            # CPU 必须 float32
            kwargs = {"torch_dtype": torch.float32}
        return kwargs


# ==================================================
# 工具类: 文本格式化
# ==================================================
class TextFormatter:
    @staticmethod
    def format_text(text):
        if not text:
            return ""
        text = unicodedata.normalize("NFKC", text)
        text = text.replace("\xa0", " ").replace("\u3000", " ").replace("\u200b", "")
        lines = [line.strip() for line in text.splitlines()]
        text = "\n".join(lines)
        text = re.sub(r"(\w+)\s+([.,;:?!])", r"\1\2", text)
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        print(f"✅ TextFormatter ran on {len(text)} chars")  # Debug 信号
        return text.strip()


# ==================================================
# 模块 1: RTF 处理与基础清洗
# ==================================================
class RTFHandler:
    @staticmethod
    def to_text(file_path):
        try:
            with open(file_path, "rb") as f:
                content = f.read().decode("cp1252", errors="ignore")

            # 1. 核心修复：SPh Media 特有格式
            content = content.replace(r"\u169?", "(c)")
            content = content.replace(r"{\b", r" {\b").replace(r"{\field", r" {\field")

            # 2. 结构物理断行
            content = content.replace("}{", "} \n {")
            content = re.sub(r"(?<!\\)\\par(?![a-zA-Z])", r"\\par\n", content)
            content = content.replace(r"\par}", r"\par\n}")

            # 3. 转换为纯文本
            text = rtf_to_text(content, errors="ignore")

            # 4. 基础清洗
            text = text.replace("\r\n", "\n").replace("\r", "\n")

            # 修复 CamelCase 粘连 (e.g. "TheGovernment" -> "The Government")
            text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)

            text = re.sub(r"\[([a-zA-Z])\]", r"\1", text)
            text = text.replace("’", "'").replace("‘", "'")
            text = re.sub(r'(READ:.*?)(")', r"\1\n\2", text)

            # 泛化版 Header/Body 粘连切割
            patterns = [
                r"(Limited)\s+([A-Z])",
                r"(Corporation)\s+([A-Z])",
                r"(Corp\.?)\s+([A-Z])",
                r"(Inc\.?)\s+([A-Z])",
                r"(Agency)\s+([A-Z])",
                r"(Reserved\.?)\s+([A-Z])",
                r"(Commission)\s+([A-Z])",
                r"(Bhd\.?)\s+([A-Z])",
                r"(English)\s+(©|Copyright|\(c\))",
            ]
            for pat in patterns:
                text = re.sub(pat, r"\1\n\n\2", text)

            # 5. 最终整理
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r"[ \t]{2,}", " ", text)

            return text.strip()
        except Exception as e:
            print(f"❌ RTF Error {file_path}: {e}")
            return ""


# ==================================================
# 结构性噪音清洗 (整篇删除)
# ==================================================
class StructuralCleaner:
    def __init__(self):
        # 跳过头条简报类内容 (Briefing / Update)
        self.SKIP_BRIEFING_PATTERN = re.compile(
            r"^\s*(Morning Briefing|Evening Update|Today's headlines|News in 5 minutes)",
            re.IGNORECASE,
        )

    def is_skippable(self, text):
        # 检查前 5 行是否命中跳过规则
        header_sample = " ".join(text.splitlines()[:5])
        return bool(self.SKIP_BRIEFING_PATTERN.search(header_sample))


# ==================================================
# 模块 2: 结构与元数据提取 (Title/Date/Source)
# ==================================================
class MetaExtractor:
    def __init__(self):
        # 严格日期正则
        self.date_pattern = re.compile(
            r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})",
            re.IGNORECASE,
        )

    def analyze_structure(self, text):
        """
        返回: (header_end_char, footer_start_char, metadata_dict)
        1. Header: 依然使用特征查找 (Date/Source)
        2. Footer: 直接定位到倒数第 2 个非空行 (Blind Cut)
        """
        lines_info = []
        cursor = 0
        for line in text.splitlines(keepends=True):
            stripped = line.strip()
            lines_info.append(
                {
                    "text": line,
                    "stripped": stripped,
                    "start": cursor,
                    "end": cursor + len(line),
                }
            )
            cursor += len(line)

        if not lines_info:
            return 0, len(text), {"title": "", "date": "", "source": ""}

        # --- A. Title ---
        title = lines_info[0]["text"].strip()

        # --- B. Header Analysis ---
        header_end_line_idx = 0
        date = ""
        source = ""

        # 1. 找 Date (Header 的核心锚点)
        date_idx = -1
        # 扫描前 20 行 (V2 逻辑)
        scan_limit = min(len(lines_info), 20)

        for i in range(scan_limit):
            line_text = lines_info[i]["text"]
            if self.date_pattern.search(line_text):
                date = self.date_pattern.search(line_text).group(0)
                date_idx = i
                break

        # 2. 找 Source (在 Date 之后)
        source_idx = -1
        if date_idx != -1:
            for k in range(date_idx + 1, scan_limit):
                cand = lines_info[k]["text"].strip()
                cand_lower = cand.lower()

                # 排除列表
                if any(
                    x in cand_lower
                    for x in ["copyright", "(c)", "©", "tagalog", "words", "english"]
                ):
                    continue
                if re.match(r"^[a-z0-9]+$", cand_lower):  # 排除纯代码
                    continue
                if len(cand) > 50:  # Source 通常不长
                    break

                source = cand
                source_idx = k
                break

        # 3. 找 Copyright
        copyright_idx = -1
        for k in range(date_idx + 1 if date_idx != -1 else 0, scan_limit):
            cand_lower = lines_info[k]["text"].lower()
            if any(
                x in cand_lower
                for x in ["copyright", "(c)", "©", "all rights reserved"]
            ):
                copyright_idx = k
                break

        # 4. 决策 Header 结束位置
        # 优先级：Copyright > Source > Date
        if copyright_idx != -1:
            header_end_line_idx = copyright_idx + 1
        elif source_idx != -1:
            header_end_line_idx = source_idx + 1
        elif date_idx != -1:
            header_end_line_idx = date_idx + 1
        else:
            header_end_line_idx = 1  # 只有标题

        # 计算 Header 字符位置
        if header_end_line_idx > 0:
            safe_idx = min(header_end_line_idx - 1, len(lines_info) - 1)
            target_line = lines_info[safe_idx]
            header_end_char = target_line["start"] + len(
                target_line["text"].rstrip("\r\n")
            )
        else:
            header_end_char = lines_info[0]["end"]

        # --- C. Footer Start Detection ---
        non_empty_lines_indices = [
            i for i, info in enumerate(lines_info) if info["stripped"]
        ]

        # 如果全文少于 4 行，可能就不存在 Footer 或者全文都是 Footer，保守起见设为末尾
        if len(non_empty_lines_indices) <= 3:
            footer_start_char = len(text)
        else:
            # 找到倒数第二行非空行的索引
            # [-1] 是最后一行 (Document ID)
            # [-2] 是倒数第二行 (Source) -> 这里是 Footer 开始的地方
            footer_start_idx = non_empty_lines_indices[-2]
            footer_start_char = lines_info[footer_start_idx]["start"]

        if header_end_line_idx > 0:
            # 为了防止 Header 和 Footer 重叠 (文章极短的情况)
            # 我们取 header_end 和 footer_start 的较小值
            safe_idx = min(header_end_line_idx - 1, len(lines_info) - 1)
            calculated_header_end = lines_info[safe_idx]["start"] + len(
                lines_info[safe_idx]["text"].rstrip("\r\n")
            )
            header_end_char = min(calculated_header_end, footer_start_char)
        else:
            header_end_char = lines_info[0]["end"]

        return (
            header_end_char,
            footer_start_char,
            {"title": title, "date": date, "source": source},
        )


# ==================================================
# 模块 3: AI 清洗 (混合架构：AI + Regex + 句子平滑)
# ==================================================
class NERCleaner:
    def __init__(self, model_configs):
        # 1. 设备选择
        self.device, self.device_info = DeviceManager.get_optimal_device()
        print(f"🤖 Noise Cleaner (DeBERTa) running on: {self.device_info['desc']}")

        self.tokenizer = None
        self.model = None

        # 结构性噪音正则
        self.PAT_STRUCTURAL_NOISE = [
            re.compile(
                r"(?:(?<=[.!?])\s*)?(More\s+On\s+This\s+Topic|Related\s+Stor(?:y|ies)).*?$",
                re.IGNORECASE | re.MULTILINE,
            ),
            re.compile(
                r"(?:(?<=[.!?])\s*)?(READ\s+MORE\s+(?:HERE|ABOUT)|Click\s+here\s+to\s+read).*?(?=\n\n|$)",
                re.IGNORECASE | re.DOTALL,
            ),
            re.compile(
                r"Sign\s+up\s+for\s+the\s+ST\s+Asian\s+Insider\s+newsletter.*?(?=\n\n|$)",
                re.IGNORECASE,
            ),
            re.compile(
                r"Disclaimer:\s+The\s+Above\s+Content\s+is\s+Auto-Translated.*",
                re.IGNORECASE | re.DOTALL,
            ),
            re.compile(r"\[Category:.*?\]", re.IGNORECASE),
            # 1. 印尼/评论文章结尾的 Bio 分割线
            # 遇到 "______" 或 "-----" 就把后面全删了
            re.compile(r"(?m)^\s*[_\-]{5,}\s*[\s\S]*$"),
            # 2. 常见的免责声明 (作为补充，防止分割线漏掉)
            re.compile(
                r"(?i)^The\s+views\s+expressed\s+are\s+(personal|solely\s+those\s+of\s+the\s+author).*$",
                re.MULTILINE,
            ),
            # 新增规则可以继续添加...
        ]

        # 2. 加载模型
        model_path = model_configs.get("NOISE_CAPTION")

        if not model_path:
            # 使用默认模型路径
            model_path = "microsoft/mdeberta-v3-base"
            print(
                f"⚠️ Warning: 'NOISE_CAPTION' not in config, using default: {model_path}"
            )

        print(f"   ↳ Loading DeBERTa from {model_path} ...")

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)

            # 根据设备选择加载参数
            model_kwargs = DeviceManager.get_model_kwargs(self.device)

            self.model = AutoModelForTokenClassification.from_pretrained(
                model_path, **model_kwargs
            )
            self.model.to(self.device)
            self.model.eval()
            self.noise_label_id = 1
        except Exception as e:
            print(f"❌ DeBERTa Model Load Failed: {e}")

    def clean(self, raw_text, header_end, footer_start, protected_keywords=None):
        """
        raw_text: 全文
        header_end / footer_start: 正文的起止位置
        protected_keywords: 如果句子包含这些词，强制不进行AI整句删除
        """
        # 1. 提取正文主体
        if header_end >= footer_start:
            return "", []

        raw_body = raw_text[header_end:footer_start].lstrip()
        # 计算偏移量以便最后返回 span (虽然现在主要用 text)
        skipped_len = len(raw_text[header_end:footer_start]) - len(raw_body)
        body_offset = header_end + skipped_len

        all_deleted_spans = []  # 用于收集所有被删除的片段

        # =========================================
        # 1. 执行 AI 扫描 (只记录位置，不生成文本)
        # =========================================
        if self.model:
            paragraphs = raw_body.splitlines(keepends=True)
            current_rel_pos = 0

            for para in paragraphs:
                if len(para.strip()) < 5:
                    current_rel_pos += len(para)
                    continue

                # 计算绝对坐标
                abs_offset = body_offset + current_rel_pos

                # 获取 AI 认为该删的片段
                _, deleted_in_para = self._ai_clean_paragraph(
                    para, abs_offset, protected_keywords
                )
                all_deleted_spans.extend(deleted_in_para)
                current_rel_pos += len(para)

        # =========================================
        # 2. 执行 Regex 扫描
        # =========================================
        # 我们在 raw_body 上直接跑正则，找到所有结构性噪音
        for pat in self.PAT_STRUCTURAL_NOISE:
            for match in pat.finditer(raw_body):
                start_idx = match.start()
                end_idx = match.end()

                # 记录 Regex 删除的片段
                all_deleted_spans.append(
                    {
                        "start": body_offset + start_idx,
                        "end": body_offset + end_idx,
                        "type": "STRUCTURAL_NOISE (Regex)",  # 前端显示为结构性噪音
                        "score": 1.0,
                        "text": match.group(),
                    }
                )

        # =========================================
        # 3. 文本重组
        # =========================================
        # 有了所有的“垃圾坐标” (AI + Regex)，现在把它们合并，
        # 然后从 raw_body 中挖掉这些部分，生成最终文本。

        # A. 将绝对坐标转回相对坐标 (Relative to raw_body)
        spans_relative = []
        for span in all_deleted_spans:
            rel_start = span["start"] - body_offset
            rel_end = span["end"] - body_offset
            # 确保坐标在 body 范围内
            rel_start = max(0, min(rel_start, len(raw_body)))
            rel_end = max(0, min(rel_end, len(raw_body)))
            if rel_start < rel_end:
                spans_relative.append((rel_start, rel_end))

        # B. 合并重叠区间 (防止 AI 和 Regex 删了同一段导致切片错误)
        spans_relative.sort(key=lambda x: x[0])
        merged_spans = []
        if spans_relative:
            curr_start, curr_end = spans_relative[0]
            for next_start, next_end in spans_relative[1:]:
                if next_start < curr_end:  # 重叠或相接
                    curr_end = max(curr_end, next_end)
                else:
                    merged_spans.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            merged_spans.append((curr_start, curr_end))

        # C. 执行裁剪 (Slicing)
        final_parts = []
        last_pos = 0
        for start, end in merged_spans:
            # 保留上一段结束到这一段开始之间的内容 (即正文)
            final_parts.append(raw_body[last_pos:start])
            last_pos = end
        # 加上最后剩余的部分
        final_parts.append(raw_body[last_pos:])

        final_body = "".join(final_parts)
        final_body = re.sub(r"\n{3,}", "\n\n", final_body).strip()

        # 返回重组后的文本 + 完整的高亮列表
        return final_body, all_deleted_spans

    def _ai_clean_paragraph(self, text, offset, protected_keywords=None):
        if not text.strip():
            return text, []

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            return_offsets_mapping=True,
            padding="longest",
        ).to(self.device)
        offsets = inputs["offset_mapping"][0].cpu().numpy()

        with torch.no_grad():
            outputs = self.model(
                input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"]
            )
            predictions = torch.argmax(outputs.logits, dim=2)[0].cpu().numpy()

        n = len(text)
        char_is_noise = np.zeros(n, dtype=bool)
        for i, (start, end) in enumerate(offsets):
            if start == end:
                continue
            if predictions[i] == self.noise_label_id:
                char_is_noise[start:end] = True

        return self._apply_sentence_logic(
            text, char_is_noise, offset, protected_keywords
        )

    def _apply_sentence_logic(self, text, char_mask, offset, protected_keywords):
        import re

        sentences_spans = []
        start = 0
        # 保持修复后的分句逻辑
        for match in re.finditer(r"(?<=[.!?])\s+", text):
            end = match.end()
            sentences_spans.append((start, end))
            start = match.end()
        sentences_spans.append((start, len(text)))

        keywords_lower = (
            [k.lower() for k in protected_keywords] if protected_keywords else []
        )
        final_chunks = []  # 这个变量其实在 V4.0 里只起辅助作用了，但保留以兼容接口
        deleted_spans = []

        for sent_start, sent_end in sentences_spans:
            sent_text = text[sent_start:sent_end]
            if not sent_text.strip():
                final_chunks.append(sent_text)
                continue

            sent_len = sent_end - sent_start
            sent_mask = char_mask[sent_start:sent_end]
            noise_ratio = np.sum(sent_mask) / sent_len if sent_len > 0 else 0

            def record_deletion(reason):
                deleted_spans.append(
                    {
                        "start": offset + sent_start,
                        "end": offset + sent_end,
                        "type": f"AI_NOISE ({reason})",
                        "score": 0.99,
                        "text": sent_text,
                    }
                )

            is_kept = True

            if any(kw in sent_text.lower() for kw in keywords_lower):
                pass  # Keep
            elif noise_ratio > 0.4:
                record_deletion("Ratio > 0.4")
                is_kept = False
            elif (
                "PHOTO:" in sent_text or "Source:" in sent_text
            ) and noise_ratio > 0.1:
                record_deletion("Visual/Source Trigger")
                is_kept = False

            if is_kept:
                final_chunks.append(sent_text)

        return "".join(final_chunks), deleted_spans

    def release_memory(self):
        print("🧹 Releasing NER model memory...")
        if hasattr(self, "model"):
            del self.model
        if hasattr(self, "tokenizer"):
            del self.tokenizer
        gc.collect()
        if self.device == "cuda":
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        elif self.device == "mps":
            torch.mps.empty_cache()
        print("✅ NER memory released.")


# ==================================================
# 模块 4a: 相关性过滤器 (语义清洗)
# ==================================================
class RelevanceFilter:
    def __init__(self):
        self.df = None
        # 1. 绝对白名单 (权重最高 - 一票通过)
        self.WHITELIST_PHRASES = [
            r"Communist Party of China",
            r"Chinese Communist Party",
            r"General Secretary of the CPC",
            r"General Secretary of the CCP",
            r"ruling party of China",
            r"CCP regime",
            r"Beijing's ruling CPC",
        ]

        # 2. 基础锚点 (必须包含其中之一才能进入下一轮)
        self.CHINA_ANCHORS = [
            "china",
            "chinese",
            "beijing",
            "xi jinping",
            "prc",
            "ccp",
            "cpc",
            "south china sea",
            "asean",
        ]

        # 3. 现代化专用正则 (针对 Topic: Modernization)
        self.MODERNIZATION_PATTERNS = [
            re.compile(r"Chinese(-|\s+)style\s+moderni[sz]ation", re.IGNORECASE),
            re.compile(r"Chinese\s+path\s+to\s+moderni[sz]ation", re.IGNORECASE),
            re.compile(r"Chinese\s+moderni[sz]ation", re.IGNORECASE),
        ]

        # 4. 局部消歧义正则 (针对 CCP / CPC 多义词)
        self.LOCAL_NOISE_PATTERNS = [
            # 菲律宾 CCP (Cultural Center)
            re.compile(r"Cultural\s+Center\s+of\s+the\s+Philippines", re.IGNORECASE),
            re.compile(
                r"\bCCP\s+(Complex|Main Theater|Little Theater|Studio|Dance|Ballet|Orchestra|Visual Arts|Children's Biennale)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(at|visit|ticket|show|exhibit|perform)\s+(at\s+)?(the\s+)?CCP\b",
                re.IGNORECASE,
            ),
            # 菲律宾/其他 CPC (Child Protection / Community)
            re.compile(r"Child\s+Protection\s+Center", re.IGNORECASE),
            re.compile(r"Valenzuela\s+City\s+CPC", re.IGNORECASE),
            re.compile(
                r"\bCPC\s+(comprising|staffed|team|doctors|social workers|barangay)\b",
                re.IGNORECASE,
            ),
            # 马新 CPC (刑法)
            re.compile(r"\bSection\s+\d+\s+of\s+(the\s+)?CPC\b", re.IGNORECASE),
            re.compile(
                r"\b(charged|investigated|detained|court)\s+under\s+(the\s+)?CPC\b",
                re.IGNORECASE,
            ),
            re.compile(r"\bCPC\s+(Code|Act|Section|provision)\b", re.IGNORECASE),
        ]

    # 快速筛选
    def is_relevant(self, text, title="", topic_mode="GENERAL"):
        combined_text = title + "\n" + text
        combined_lower = combined_text.lower()

        # 1. 绝对白名单
        for phrase in self.WHITELIST_PHRASES:
            if phrase.lower() in combined_lower:
                return True, "WHITELIST_MATCH"

        # 2. 局部消歧 (Regex)
        for pat in self.LOCAL_NOISE_PATTERNS:
            if pat.search(combined_text):
                return False, f"NOISE_PATTERN: {pat.pattern}"

        # 3. 话题分流
        if topic_mode == "MODERNIZATION":
            for pat in self.MODERNIZATION_PATTERNS:
                if pat.search(combined_text):
                    return True, "MODERNIZATION_MATCH"
            pass  # 继续走后续的 China 检查

        elif topic_mode == "STRICT_CPC":
            # 必须有缩写
            has_abbr = (
                "ccp" in combined_lower.split() or "cpc" in combined_lower.split()
            )
            if not has_abbr:
                return False, "NO_CPC_ABBR"
            # 只要有缩写，就放行给语义模型去判断是不是"Cultural Center"
            return True, "CPC_ABBR_FOUND"

        # 4. 通用门槛：检查基础锚点
        # 只要包含 "China", "Beijing" 等词，就放行进入语义分析
        for anchor in self.CHINA_ANCHORS:
            if anchor in combined_lower:
                return True, "ANCHOR_MATCH"

        return False, "NO_CHINA_KEYWORDS"


## ==================================================
# 模块 4b: 语义相关性过滤器 (Sentence-BERT)
# ==================================================
class SemanticRelevanceFilter:
    def __init__(self, config, threshold=0.15):
        """
        threshold: 正向相似度的最低门槛。即使没触犯负向规则，如果离政治太远也不要。
        """
        self.config = config
        self.threshold = threshold

        # 1. 设备选择
        self.device, self.device_info = DeviceManager.get_optimal_device()
        print(f"🧠 Semantic Engine (MiniLM) running on: {self.device_info['desc']}")

        # 2. 获取模型路径
        model_path = config.get(
            "SEMANTIC_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )

        # 3. 加载模型
        opt_kwargs = DeviceManager.get_model_kwargs(self.device)
        print(f"   ↳ Loading Semantic Model from: {model_path} ...")

        try:
            # 尝试本地加载
            self.model = SentenceTransformer(
                model_path, device=self.device, model_kwargs=opt_kwargs
            )
        except Exception as e:
            print(f"❌ Failed to load Semantic Model: {e}")
            # 尝试从 HuggingFace 下载
            print("   ↳ Fallback: Downloading 'all-MiniLM-L6-v2' from HuggingFace...")
            self.model = SentenceTransformer("all-MiniLM-L6-v2", device=self.device)

        # 4. 加载规则 (配置)
        self.config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "semantic_config.json"
        )
        self.load_concepts()
        self.update_embeddings()

    # === 定义锚点 ===
    def load_concepts(self):
        """从 JSON 加载概念，如果不存在则使用默认值"""
        defaults = {
            # 1. 我们想要的内容 (政治、外交、战略经济)
            "positive": [
                "Diplomacy and bilateral relations between countries",
                "Government official visits and high-level meetings",
                "Belt and Road Initiative and infrastructure projects",
                "South China Sea disputes and maritime security",
                "International trade agreements and economic cooperation",
                "Chinese state-owned enterprises investment",
                "Foreign ministry statements and embassies",
                "Political ideology and party congress",
            ],
            "negative": [
                # 2. 我们不想要的内容 (纯商业、生活、广告)
                "Commercial banking awards and financial performance reports",
                "Retail promotions, shopping, and restaurant food reviews",
                "Travel holiday packages and tourism advertisements",
                "Sports match results and athlete news",
                "Entertainment, celebrity gossip, and movies",
                "Routine crime reports and local accidents",
                "Stock market fluctuations and corporate shareholders meeting",
                "Art exhibitions and cultural performances tickets",
                "Newspaper publisher notes, editorial disclaimers, and advertising supplements",
            ],
        }

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.positive_concepts = data.get("positive", defaults["positive"])
                    self.negative_concepts = data.get("negative", defaults["negative"])
                print("✅ Loaded semantic config from file.")
            except Exception as e:
                print(f"⚠️ Config load failed ({e}), using defaults.")
                self.positive_concepts = defaults["positive"]
                self.negative_concepts = defaults["negative"]
        else:
            print("ℹ️ No config file found, creating default.")
            self.positive_concepts = defaults["positive"]
            self.negative_concepts = defaults["negative"]
            self.save_concepts()

    # 保存当前概念到 JSON
    def save_concepts(self):
        try:
            data = {
                "positive": self.positive_concepts,
                "negative": self.negative_concepts,
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Failed to save config: {e}")

    # 当概念改变时，重新计算 Embeddings
    def update_embeddings(self):
        if hasattr(self, "model"):
            self.pos_embedding = self.model.encode(
                " ".join(self.positive_concepts), convert_to_tensor=True
            )
            self.neg_embedding = self.model.encode(
                " ".join(self.negative_concepts), convert_to_tensor=True
            )

        # 预计算锚点的向量 (加速后续推理)
        # 我们把所有正向概念拼成一个大的语义向量，负向同理
        self.pos_embedding = self.model.encode(
            " ".join(self.positive_concepts), convert_to_tensor=True
        )
        self.neg_embedding = self.model.encode(
            " ".join(self.negative_concepts), convert_to_tensor=True
        )

    def is_relevant(self, text, title=""):
        """
        返回: (bool, reason, scores)
        """
        # 组合标题和正文的前 800 个字符 (开头通常包含主旨)
        # 没必要读全文，既省时间又防止被后文的噪音干扰
        content_snippet = f"{title}. {text[:800]}"

        # 计算当前文章的向量
        doc_embedding = self.model.encode(content_snippet, convert_to_tensor=True)

        # 计算余弦相似度
        score_pos = util.cos_sim(doc_embedding, self.pos_embedding).item()
        score_neg = util.cos_sim(doc_embedding, self.neg_embedding).item()

        scores_info = f"[Pos: {score_pos:.3f} | Neg: {score_neg:.3f}]"

        # === 判定逻辑 ===

        # 1. 负向压倒正向：虽然有一点点政治味，但更像是一篇广告/财报
        # 比如：BIBD Bank won an award in Beijing. (Beijing提供了pos分，但Bank Award提供了巨大的neg分)
        if score_neg > score_pos:
            return False, f"SEMANTIC_NOISE {scores_info}"

        # 2. 正向分数太低：这文章可能谁都不沾边（比如讲澳洲天气的）
        if score_pos < self.threshold:
            return False, f"LOW_RELEVANCE {scores_info}"

        # 3. 通过筛选
        return True, f"SEMANTIC_MATCH {scores_info}"

    def release_memory(self):
        print("🧠 Releasing Semantic Model (MiniLM) memory...")
        if hasattr(self, "model"):
            del self.model
        if hasattr(self, "pos_embedding"):
            del self.pos_embedding
        if hasattr(self, "neg_embedding"):
            del self.neg_embedding
        gc.collect()
        if self.device == "cuda":
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        elif self.device == "mps":
            try:
                torch.mps.empty_cache()
            except:
                pass
        print("✅ Semantic Model memory released.")


# ==================================================
# 模块 5: 流水线控制器
# ==================================================
class CorpusPipeline:
    def __init__(self, model_configs):
        # 1. 初始化工具模块
        self.rtf_handler = RTFHandler()
        self.struct_cleaner = StructuralCleaner()
        self.meta_extractor = MetaExtractor()

        # 2. 初始化 AI 清洗器和语义过滤器
        self.cleaner = NERCleaner(model_configs)
        self.semantic_filter = SemanticRelevanceFilter(model_configs, threshold=0.15)

        # 3. 初始化相关性过滤器
        self.relevance_filter = RelevanceFilter()

    def process_folder(
        self, input_dir, output_base_dir=None, recursive=False, progress_callback=None
    ):
        if self.cleaner is None or self.semantic_filter is None:
            print("❌ Error: Pipeline models not initialized correctly.")
            return

        all_files = []

        if recursive:
            # === 模式 A: 递归 (Batch Mode) ===
            print(f"🔄 Scanning RECURSIVELY in: {input_dir}")
            for root, _, files in os.walk(input_dir):
                for f in files:
                    if f.lower().endswith(".rtf"):
                        all_files.append(os.path.join(root, f))
        else:
            # === 模式 B: 单层 (Single Folder Mode) ===
            print(f"⏺️ Scanning SINGLE LEVEL in: {input_dir}")
            if os.path.exists(input_dir):
                for f in os.listdir(input_dir):
                    full_path = os.path.join(input_dir, f)
                    if os.path.isfile(full_path) and f.lower().endswith(".rtf"):
                        all_files.append(full_path)

        if not all_files:
            print("⚠️ No RTF files found.")
            return

        # 进度统计
        total_files = len(all_files)
        processed_count = 0
        print(f"🚀 Found {total_files} files.")

        files_by_folder = {}
        for f in all_files:
            folder = os.path.dirname(f)
            if folder not in files_by_folder:
                files_by_folder[folder] = []
            files_by_folder[folder].append(f)

        print(f"📂 Grouped into {len(files_by_folder)} folders.")

        for folder, files in files_by_folder.items():
            # 防止在根目录生成 /output (如果是递归模式)
            if recursive and os.path.normpath(folder) == os.path.normpath(input_dir):
                print(f"⏩ Skipping root folder output: {folder}")
                continue
            rel_path = os.path.relpath(folder, input_dir)
            out_folder = os.path.join(folder, "output")
            os.makedirs(out_folder, exist_ok=True)

            # 友好显示路径
            display_path = rel_path
            if rel_path == ".":
                display_path = f"{os.path.basename(input_dir)} (Root)"

            # 根据文件夹名称判断 Topic Mode
            folder_name_lower = os.path.basename(folder).lower()
            topic_mode = "GENERAL_CHINA"  # 默认

            if "modern" in folder_name_lower:  # 覆盖 modernization, modernisation
                topic_mode = "MODERNIZATION"
            elif (
                "cpc" in folder_name_lower
                or "ccp" in folder_name_lower
                or "party" in folder_name_lower
            ):
                topic_mode = "STRICT_CPC"

            # 打印一下当前的模式，方便调试确认
            print(f"📂 Processing: {display_path} | Mode: {topic_mode}")

            frontend_data_list = []
            csv_logs = []  # 进度日志

            # 构建保护词列表
            protected_kws = []
            try:
                # 从 Gatekeeper 获取白名单
                protected_kws.extend(self.relevance_filter.WHITELIST_PHRASES)
                # 从 Semantic Filter 获取正向概念里的关键词 (简单分词)
                # 简单加一些核心词，不用太复杂
                protected_kws.extend(
                    [
                        "modernization",
                        "modernisation",
                        "bilateral",
                        "summit",
                        "relations",
                    ]
                )
                protected_kws = list(set([k for k in protected_kws if len(k) > 2]))
            except Exception as e:
                print(f"⚠️ 关键词提取警告: {e}")

            for rtf_path in files:
                processed_count += 1
                # 发送进度给 Electron
                if progress_callback:
                    progress_callback(
                        processed_count,
                        total_files,
                        f"Processing: {os.path.basename(rtf_path)}",
                    )

                # A. 读取
                raw_text = self.rtf_handler.to_text(rtf_path)
                if not raw_text:
                    continue

                temp_title = raw_text.split("\n")[0] if raw_text else ""

                # 沙漏过滤器
                # === 过滤第一步：关键词===
                is_kept_gate, gate_reason = self.relevance_filter.is_relevant(
                    raw_text, temp_title, topic_mode=topic_mode
                )

                if not is_kept_gate:
                    print(
                        f"🚫 [Gatekeeper Skipped] {os.path.basename(rtf_path)}: {gate_reason}"
                    )
                    continue

                # === 过滤第二步：语义===
                # 只有通过了第一步的文章才会进这里
                is_kept_sem, sem_reason = self.semantic_filter.is_relevant(
                    raw_text, temp_title
                )

                if not is_kept_sem:
                    print(
                        f"🗑️ [Semantic Skipped] {os.path.basename(rtf_path)}: {sem_reason}"
                    )
                    continue

                # print(f"✅ [Kept] {os.path.basename(rtf_path)}: {sem_reason}")

                # B. 过滤 Briefing
                if self.struct_cleaner.is_skippable(raw_text):
                    continue

                # C. 结构分析
                h_end, f_start, meta = self.meta_extractor.analyze_structure(raw_text)

                # D. NER 清洗
                final_clean_body, body_noise = self.cleaner.clean(
                    raw_text, h_end, f_start, protected_keywords=protected_kws
                )

                # 格式化 (Formatting)
                final_clean_body = TextFormatter.format_text(final_clean_body)

                # E. 构建高亮
                highlights = []
                if h_end > 0:
                    highlights.append({"start": 0, "end": h_end, "type": "HEADER"})
                highlights.extend(body_noise)
                if f_start < len(raw_text):
                    highlights.append(
                        {"start": f_start, "end": len(raw_text), "type": "FOOTER"}
                    )

                # F. 保存 TXT
                file_stem = os.path.splitext(os.path.basename(rtf_path))[0]
                if file_stem.startswith("._"):
                    file_stem = file_stem[2:]
                clean_filename = re.sub(r'[\\/*?:"<>|]', "_", file_stem) + ".txt"

                out_txt_path = os.path.join(out_folder, clean_filename)
                content = (
                    f"<title>{meta['title']}</title>\n"
                    f"<date>{meta['date']}</date>\n"
                    f"<source>{meta['source']}</source>\n"
                    f"<body>\n{final_clean_body}\n</body>"
                )
                with open(out_txt_path, "w", encoding="utf-8") as f:
                    f.write(content)

                self._append_to_folder_logs(
                    out_folder,
                    {
                        "filename": clean_filename,
                        "original_text": raw_text,
                        "cleaned_body": final_clean_body,
                        "highlights": [],
                        "metadata": meta,
                    },
                    {
                        "Filename": clean_filename,
                        "Title": meta["title"],
                        "Date": meta["date"],
                        "Source": meta["source"],
                        "Checked": "No",
                    },
                )
                # G. 数据收集
                frontend_data_list.append(
                    {
                        "filename": clean_filename,
                        "original_text": raw_text,
                        "cleaned_body": final_clean_body,
                        "highlights": highlights,
                        "metadata": meta,
                    }
                )

                # H. 收集 CSV 日志
                csv_logs.append(
                    {
                        "Filename": clean_filename,
                        "Title": meta["title"],
                        "Date": meta["date"],
                        "Source": meta["source"],
                        "Checked": "No",
                    }
                )

            # 保存 JSON
            if frontend_data_list:
                json_path = os.path.join(out_folder, "frontend_diff.json")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(frontend_data_list, f, ensure_ascii=False, indent=2)

            # 保存 CSV
            if csv_logs:
                pd.DataFrame(csv_logs).to_csv(
                    os.path.join(out_folder, "progress_log.csv"),
                    index=False,
                    encoding="utf-8-sig",
                )

    def _append_to_folder_logs(self, output_dir, frontend_data, csv_data):
        """
        辅助函数：向指定 folders 的 logs 追加数据。
        如果文件不存在则创建，存在则读取后追加 (避免覆盖同目录下的其他文件记录)
        """

        # === 1. 处理 JSON (frontend_diff.json) ===
        json_path = os.path.join(output_dir, "frontend_diff.json")
        current_list = []

        # 读取旧数据
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        current_list = json.loads(content)
            except Exception as e:
                print(f"⚠️ Error reading JSON log: {e}")

        # 去重更新：如果列表中已经有了这个 filename，先删掉旧的，再加新的
        current_list = [
            item
            for item in current_list
            if item.get("filename") != frontend_data["filename"]
        ]
        current_list.append(frontend_data)

        # 写入
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(current_list, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Failed to write JSON log: {e}")

        # === 2. 处理 CSV (progress_log.csv) ===
        csv_path = os.path.join(output_dir, "progress_log.csv")
        df = pd.DataFrame()

        # 读取旧数据
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
            except Exception as e:
                print(f"⚠️ Error reading CSV log: {e}")

        new_row = pd.DataFrame([csv_data])

        # 去重更新
        if not df.empty and "Filename" in df.columns:
            # 删除旧记录
            df = df[df["Filename"] != csv_data["Filename"]]
            # 追加新记录
            df = pd.concat([df, new_row], ignore_index=True)
        else:
            # 如果是空表，直接赋值
            df = new_row

        # 写入 (utf-8-sig 防止 Excel 打开乱码)
        try:
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        except Exception as e:
            print(f"❌ Failed to write CSV log: {e}")

    def dispose(self):
        print("🗑️ Disposing Pipeline resources...")
        if hasattr(self, "cleaner"):
            self.cleaner.release_memory()
        if hasattr(self, "semantic_filter"):
            self.semantic_filter.release_memory()
        self.cleaner = None
        self.semantic_filter = None
        self.seen_hashes = None
        gc.collect()
        print("✨ Pipeline resources completely freed.")


if __name__ == "__main__":
    # 路径配置
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = current_script_dir

    # 动态拼接模型路径
    noise_model_path = os.path.join(
        project_root, "models", "noise-cleaner-deberta-v2", "final"
    )
    semantic_model_path = os.path.join(project_root, "models", "all-MiniLM-L6-v2")

    MODEL_CONFIGS = {
        "NOISE_CAPTION": noise_model_path,
        "SEMANTIC_MODEL": semantic_model_path,
    }

    INPUT_DIR = os.path.join(project_root, "Corpus")
    OUTPUT_DIR = os.path.join(project_root, "Cleaned_Corpus")

    if not os.path.exists(INPUT_DIR):
        print(f"⚠️ Input Directory not found: {INPUT_DIR}")
    else:
        pipeline = CorpusPipeline(MODEL_CONFIGS)
        try:
            pipeline.process_folder(INPUT_DIR, OUTPUT_DIR)
        finally:
            pipeline.dispose()
