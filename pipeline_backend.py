import os
import re
import json
import pandas as pd
import nltk
import torch
import difflib
from pathlib import Path
from transformers import pipeline

# --- 依赖检查 ---
try:
    from striprtf.striprtf import rtf_to_text
except ImportError:
    raise ImportError("Missing dependency: striprtf. Please run: pip install striprtf")

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)


class CorpusPipeline:
    def __init__(self, model_path):
        self.device_id = 0 if torch.cuda.is_available() else -1
        device_name = "GPU (CUDA)" if self.device_id == 0 else "CPU"
        print(f"🤖 加载模型: {model_path}")
        print(f"⚙️ 运行设备: {device_name}")

        try:
            self.classifier = pipeline(
                "text-classification",
                model=model_path,
                tokenizer=model_path,
                device=self.device_id,
            )
        except Exception as e:
            print(f"❌ GPU 加载失败: {e}")
            self.classifier = pipeline(
                "text-classification", model=model_path, tokenizer=model_path, device=-1
            )

    def clean_rtf(self, rtf_path):
        try:
            with open(rtf_path, "rb") as f:
                content = f.read().decode("cp1252", errors="ignore")
            content = content.replace(r"{\b", r" {\b").replace(r"{\field", r" {\field")
            text = rtf_to_text(content, errors="ignore")

            # 强制统一换行符，保证坐标对齐
            text = text.replace("\r\n", "\n").replace("\r", "\n")

            text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
            text = re.sub(r"\[([a-zA-Z])\]", r"\1", text)
            text = text.replace("’", "'").replace("‘", "'")
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r"[ \t]{2,}", " ", text)
            text = re.sub(r'(READ:.*?)(")', r"\1\n\2", text)
            return text.strip()
        except:
            return ""

    def get_structure_indices(self, text):
        """
        【V10.0】
        核心修复：计算 Header 结束坐标时，主动剔除末尾换行符，
        解决 Label Studio "end=223 vs 222" 的渲染越界问题。
        """
        lines_info = []
        cursor = 0
        for line in text.splitlines(keepends=True):
            if line.strip():
                lines_info.append(
                    {"text": line, "start": cursor, "end": cursor + len(line)}
                )
            cursor += len(line)

        if not lines_info:
            return 0, len(text), ("", "", "")

        # ==========================================
        # A. Title (第一行)
        # ==========================================
        title = lines_info[0]["text"].strip()

        # ==========================================
        # B. 确定 Header 结束行 (Visual Boundary)
        # ==========================================
        header_end_line_idx = 0
        copyright_content = ""

        # 扫描前 60 行寻找 Copyright
        for i, info in enumerate(lines_info[:60]):
            txt_lower = info["text"].lower()
            if "copyright" in txt_lower or "(c)" in txt_lower:
                # 不再强制年份，只要像版权声明就行
                if len(txt_lower) < 200:
                    header_end_line_idx = i + 1
                    copyright_content = info["text"]
                    break

        # 兜底：Date + 3行
        date_pattern = re.compile(
            r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})",
            re.IGNORECASE,
        )
        if header_end_line_idx == 0:
            for i, info in enumerate(lines_info[:25]):
                if date_pattern.search(info["text"]):
                    header_end_line_idx = i + 3
                    break

        # -------------------------------------------------------
        # 【关键修复点 START】 坐标回缩 (Trim Newline)
        # -------------------------------------------------------
        if header_end_line_idx > 0:
            safe_idx = min(header_end_line_idx - 1, len(lines_info) - 1)

            # 获取这一行的完整原始文本 (包含 \n)
            target_line = lines_info[safe_idx]
            raw_content = target_line["text"]

            # 去掉末尾的换行符 (\r 或 \n)，计算“可见字符”的长度
            # 注意：rstrip() 不带参数会去掉空格，我们只去掉换行符以防万一
            visible_content = raw_content.rstrip("\r\n")

            # 新的 end = 该行起点 + 可见内容长度
            # 这样 end 就会指向 \n 之前的位置 (例如 222)，而不是 \n 之后 (223)
            header_end_char = target_line["start"] + len(visible_content)
        else:
            header_end_char = lines_info[min(1, len(lines_info) - 1)]["end"]
        # -------------------------------------------------------
        # 【关键修复点 END】
        # -------------------------------------------------------

        # ==========================================
        # C. 确定 Footer 开始点
        # ==========================================
        footer_start_line_idx = len(lines_info)

        for i in range(len(lines_info) - 1, max(-1, len(lines_info) - 15), -1):
            line = lines_info[i]["text"]
            is_footer = False
            if re.search(r"^Document\s+[A-Z0-9]+", line) or line.startswith("ID:"):
                is_footer = True
            elif any(
                kw in line
                for kw in [
                    "Corporation",
                    "Corp.",
                    "Inc.",
                    "Limited",
                    "Ltd.",
                    "Publishing",
                    "Rights Reserved",
                    "Group",
                ]
            ):
                if len(line) < 100:
                    is_footer = True
            elif "email :" in line.lower() or "contact :" in line.lower():
                if len(line) < 100:
                    is_footer = True

            if is_footer:
                footer_start_line_idx = i
            else:
                if len(line) > 50 or line.endswith("."):
                    break
                break

        if footer_start_line_idx < len(lines_info):
            footer_start_char = lines_info[footer_start_line_idx]["start"]
        else:
            footer_start_char = len(text)

        # ==========================================
        # D. Metadata 提取
        # ==========================================
        header_lines = lines_info[:header_end_line_idx]

        date = ""
        date_idx_in_header = -1
        for i, info in enumerate(header_lines):
            if date_pattern.search(info["text"]):
                date = info["text"].strip()
                date_idx_in_header = i
                break

        source = ""
        if date_idx_in_header != -1:
            for k in range(date_idx_in_header + 1, len(header_lines)):
                cand = header_lines[k]["text"].strip()
                cand_lower = cand.lower()
                if "copyright" in cand_lower or "(c)" in cand_lower:
                    continue
                if cand_lower in ["english", "tagalog", "filipino"]:
                    continue
                if re.match(r"^[A-Z0-9]+$", cand):
                    continue
                if re.search(r"^\d+\s+words", cand_lower):
                    continue
                source = cand
                break

        if not source and copyright_content:
            temp = re.sub(
                r"\(c\)|copyright|all rights reserved|\d{4}",
                "",
                copyright_content,
                flags=re.IGNORECASE,
            ).strip()
            temp = temp.strip(" .,-")
            if len(temp) > 2:
                source = temp

        return header_end_char, footer_start_char, (title, date, source)

    def generate_clean_body_and_labels(self, raw_text, header_end, footer_start):
        if header_end >= footer_start:
            return "", []

        raw_body = raw_text[header_end:footer_start]
        ls_predictions = []

        # 1. HEADER (灰色)
        if header_end > 0:
            ls_predictions.append(
                {
                    "from_name": "label",
                    "to_name": "text",
                    "type": "labels",
                    "value": {
                        "start": 0,
                        "end": header_end,
                        "text": raw_text[:header_end],
                        "labels": ["HEADER"],
                    },
                    "score": 1.0,
                }
            )

        # 2. FOOTER (灰色)
        if footer_start < len(raw_text):
            ls_predictions.append(
                {
                    "from_name": "label",
                    "to_name": "text",
                    "type": "labels",
                    "value": {
                        "start": footer_start,
                        "end": len(raw_text),
                        "text": raw_text[footer_start:],
                        "labels": ["FOOTER"],
                    },
                    "score": 1.0,
                }
            )

        # 3. Body 清洗
        spans = list(nltk.tokenize.PunktSentenceTokenizer().span_tokenize(raw_body))
        batch_texts = []
        batch_indices = []

        for idx, (start, end) in enumerate(spans):
            sent_text = raw_body[start:end]
            clean_sent = sent_text.replace("\n", " ").strip()
            if len(clean_sent) > 2:
                batch_texts.append(clean_sent)
                batch_indices.append(idx)

        if not batch_texts:
            return raw_body.strip(), ls_predictions

        try:
            results = self.classifier(
                batch_texts, truncation=True, max_length=512, batch_size=16
            )
        except:
            return raw_body.strip(), ls_predictions

        keep_mask = [True] * len(spans)

        for i, res in enumerate(results):
            span_idx = batch_indices[i]
            sent_text = batch_texts[i]

            is_noise = False
            if res["label"] in ["NOISE", "LABEL_0", 0]:
                is_noise = True
            if re.search(
                r"^(Photo|Image|Source|Figure)\s*(:|by)\s+", sent_text, re.IGNORECASE
            ):
                is_noise = True
            elif "http" in sent_text or "www." in sent_text:
                is_noise = True
            elif sent_text.startswith("READ:") or "Click here" in sent_text:
                is_noise = True
            elif sent_text.isupper() and len(sent_text) < 50:
                is_noise = True

            if is_noise:
                keep_mask[span_idx] = False

        stop_cutting = False
        for i in range(len(spans) - 1, -1, -1):
            if not keep_mask[i]:
                continue
            if stop_cutting:
                break

            start, end = spans[i]
            sent_text = raw_body[start:end].replace("\n", " ")

            is_bio = False
            if re.search(r"^[-–—]\s*[A-Za-z\s\.]+$", sent_text):
                is_bio = True
            elif (
                "is a writer" in sent_text
                or "can be reached" in sent_text
                or "email" in sent_text.lower()
            ):
                is_bio = True

            if is_bio:
                keep_mask[i] = False
            else:
                if len(sent_text) > 30:
                    stop_cutting = True

        final_sentences = []
        for i, (start, end) in enumerate(spans):
            if keep_mask[i]:
                final_sentences.append(raw_body[start:end].strip())
            else:
                global_start = header_end + start
                global_end = header_end + end
                ls_predictions.append(
                    {
                        "from_name": "label",
                        "to_name": "text",
                        "type": "labels",
                        "value": {
                            "start": global_start,
                            "end": global_end,
                            "text": raw_body[start:end],
                            "labels": ["NOISE"],
                        },
                        "score": 0.99,
                    }
                )

        return "\n\n".join(final_sentences), ls_predictions

    def process_folder(self, input_dir, output_base_dir, progress_callback=None):
        files = []
        for root, _, fnames in os.walk(input_dir):
            for f in fnames:
                if f.lower().endswith(".rtf"):
                    files.append(os.path.join(root, f))

        total_files = len(files)
        files_by_folder = {}
        for f in files:
            folder = os.path.dirname(f)
            if folder not in files_by_folder:
                files_by_folder[folder] = []
            files_by_folder[folder].append(f)

        processed_count = 0

        for folder, folder_files in files_by_folder.items():
            ls_diff_tasks = []
            csv_data = []

            rel_path = os.path.relpath(folder, input_dir)
            out_folder = os.path.join(output_base_dir, rel_path)
            if not os.path.exists(out_folder):
                os.makedirs(out_folder)

            csv_path = os.path.join(out_folder, "progress_log.csv")
            old_checked = {}
            if os.path.exists(csv_path):
                try:
                    df_old = pd.read_csv(csv_path)
                    for _, row in df_old.iterrows():
                        old_checked[str(row["Filename"])] = row.get("Checked", "No")
                except:
                    pass

            for rtf_path in folder_files:
                processed_count += 1
                if progress_callback:
                    progress_callback(
                        processed_count,
                        total_files,
                        f"处理: {os.path.basename(rtf_path)}",
                    )

                raw_text = self.clean_rtf(rtf_path)
                if not raw_text:
                    continue

                # 1. 提取结构 (含 Header/Footer 坐标)
                header_end, footer_start, meta = self.get_structure_indices(raw_text)
                title, date, source = meta

                # 2. 清洗 Body 并生成标签
                clean_body, ls_labels = self.generate_clean_body_and_labels(
                    raw_text, header_end, footer_start
                )

                file_stem = os.path.splitext(os.path.basename(rtf_path))[0]
                txt_filename = re.sub(r'[\\/*?:"<>|]', "_", file_stem) + ".txt"
                txt_path = os.path.join(out_folder, txt_filename)

                # 3. 保存 TXT
                final_content = f"<TITLE>{title}</TITLE>\n<DATE>{date}</DATE>\n<SOURCE>{source}</SOURCE>\n<BODY>\n{clean_body}\n</BODY>"
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(final_content)

                # 4. 保存 Diff 记录
                ls_diff_tasks.append(
                    {
                        "data": {
                            "text": raw_text,
                            "file_id": f"{os.path.basename(out_folder)}_{file_stem}",
                        },
                        "predictions": [
                            {"model_version": "v7_fix", "result": ls_labels}
                        ],
                    }
                )

                # 5. 保存 CSV 记录
                csv_data.append(
                    {
                        "Filename": txt_filename,
                        "Title": title,
                        "Date": date,
                        "Source": source,
                        "Checked": old_checked.get(txt_filename, "No"),
                    }
                )

            if csv_data:
                pd.DataFrame(csv_data).to_csv(
                    csv_path, index=False, encoding="utf-8-sig"
                )

            if ls_diff_tasks:
                ls_path = os.path.join(out_folder, "diff_check.json")
                with open(ls_path, "w", encoding="utf-8") as f:
                    json.dump(ls_diff_tasks, f, ensure_ascii=False, indent=2)
