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
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

class CorpusPipeline:
    def __init__(self, model_path):
        self.device_id = 0 if torch.cuda.is_available() else -1
        device_name = "GPU (CUDA)" if self.device_id == 0 else "CPU"
        print(f"🤖 加载模型: {model_path}")
        print(f"⚙️ 运行设备: {device_name}")
        
        try:
            self.classifier = pipeline("text-classification", model=model_path, tokenizer=model_path, device=self.device_id)
        except Exception as e:
            print(f"❌ GPU 加载失败: {e}")
            self.classifier = pipeline("text-classification", model=model_path, tokenizer=model_path, device=-1)
            
    def clean_rtf(self, rtf_path):
        try:
            with open(rtf_path, "rb") as f:
                content = f.read().decode("cp1252", errors="ignore")
            
            # 1. 源码层预处理
            content = content.replace(r'\u169?', '(c)') # SPH 特有乱码修复
            content = content.replace(r"{\b", r" {\b").replace(r"{\field", r" {\field")
            
            # 物理断行注入
            content = content.replace(r"\par}", r"\par} __BR__ ")
            content = content.replace(r"}{", r"} __BR__ {")
            content = re.sub(r'\\par(?![a-zA-Z])', r'\\par __BR__ ', content)
            
            # 2. 转换
            text = rtf_to_text(content, errors="ignore")
            
            # 3. 文本层后处理
            text = text.replace("__BR__", "\n")
            text = text.replace('\r\n', '\n').replace('\r', '\n')
            
            # 【修复 1】统一版权符号，确保后续正则能匹配到
            text = text.replace('©', '(c)')
            
            text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
            text = re.sub(r'\[([a-zA-Z])\]', r'\1', text)
            text = text.replace("’", "'").replace("‘", "'")
            
            # 强力拆解粘连
            text = re.sub(r'(READ:.*?)(\s)([A-Z])', r'\1\n\3', text)
            text = re.sub(r'(ST PHOTO:.*?)(\s)([A-Z])', r'\1\n\3', text)
            text = re.sub(r'((?:Image|Photo)\s*(?:by|:).*?)(\s)([A-Z])', r'\1\n\3', text, flags=re.IGNORECASE)
            
            text = re.sub(r'(\n\s*){3,}', '\n\n', text)
            # 清理行首行尾空格
            text = re.sub(r'[ \t]+', ' ', text)
            
            patterns = [
                r'(Limited)\s+([A-Z])', r'(Corporation)\s+([A-Z])', r'(Corp\.?)\s+([A-Z])',
                r'(Inc\.?)\s+([A-Z])', r'(Agency)\s+([A-Z])', r'(Reserved\.?)\s+([A-Z])',
                r'(Commission)\s+([A-Z])', r'(Bhd\.?)\s+([A-Z])', r'(Sdn\.?)\s+([A-Z])',
                r'(English)\s+(©|Copyright|\(c\))',
            ]
            for pat in patterns:
                text = re.sub(pat, r'\1\n\n\2', text)

            return text.strip()
        except: return ""

    def get_structure_indices(self, text):
        lines_info = [] 
        cursor = 0
        for line in text.splitlines(keepends=True):
            if line.strip(): 
                 lines_info.append({"text": line, "start": cursor, "end": cursor + len(line)})
            cursor += len(line)

        if not lines_info: return 0, len(text), ("", "", "")

        # --- A. Title ---
        title = lines_info[0]["text"].strip()

        # --- B. Header End (Copyright) ---
        header_end_line_idx = 0
        copyright_content = ""
        
        for i, info in enumerate(lines_info[:60]):
            txt_lower = info["text"].lower()
            # 【修复 2】同时检查 (c) 和 copyright
            if ("copyright" in txt_lower or "(c)" in txt_lower):
                if len(txt_lower) < 200: 
                    header_end_line_idx = i + 1
                    copyright_content = info["text"].strip()
                    break
        
        # 兜底
        date_pattern = re.compile(r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})', re.IGNORECASE)
        if header_end_line_idx == 0:
            for i, info in enumerate(lines_info[:25]):
                if date_pattern.search(info["text"]):
                    header_end_line_idx = i + 3
                    break
        
        # 计算 Header 结束坐标 (含微调)
        if header_end_line_idx > 0:
            safe_idx = min(header_end_line_idx - 1, len(lines_info) - 1)
            
            # 【修复 3】只取可见字符长度，剔除换行符，防止 Label Studio 越界
            target_line = lines_info[safe_idx]
            visible_len = len(target_line["text"].rstrip('\r\n'))
            header_end_char = target_line["start"] + visible_len
        else:
            header_end_char = lines_info[min(1, len(lines_info)-1)]["end"]

        # --- C. Footer Start ---
        footer_start_line_idx = len(lines_info)
        for i in range(len(lines_info) - 1, max(-1, len(lines_info) - 15), -1):
            line = lines_info[i]["text"]
            is_footer = False
            if re.search(r'^Document\s+[A-Z0-9]+', line) or line.startswith("ID:"): is_footer = True
            elif any(kw in line for kw in ["Corporation", "Corp.", "Inc.", "Limited", "Ltd.", "Publishing", "Rights Reserved", "Group"]): 
                if len(line) < 100: is_footer = True
            elif "email :" in line.lower() or "contact :" in line.lower():
                 if len(line) < 100: is_footer = True

            if is_footer:
                footer_start_line_idx = i
            else:
                if len(line) > 50 or line.endswith("."): break
                break

        if footer_start_line_idx < len(lines_info):
            footer_start_char = lines_info[footer_start_line_idx]["start"]
        else:
            footer_start_char = len(text)

        # --- D. Metadata ---
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
                if "copyright" in cand_lower or "(c)" in cand_lower: continue
                if cand_lower in ["english", "tagalog", "filipino"]: continue
                if re.match(r'^[A-Z0-9]+$', cand): continue 
                if re.search(r'^\d+\s+words', cand_lower): continue
                source = cand
                break
        
        if not source and copyright_content:
            temp = re.sub(r'\(c\)|copyright|all rights reserved|\d{4}', '', copyright_content, flags=re.IGNORECASE).strip()
            temp = temp.strip(' .,-')
            if len(temp) > 2: source = temp

        return header_end_char, footer_start_char, (title, date, source)

    def generate_clean_body_and_labels(self, raw_text, header_end, footer_start):
        if header_end >= footer_start:
            return "", []

        # 1. 截取 Raw Body
        raw_body = raw_text[header_end:footer_start].lstrip()
        # 计算偏移量用于坐标对齐
        skipped_len = len(raw_text[header_end:footer_start]) - len(raw_body)
        body_offset = header_end + skipped_len
        
        ls_predictions = []
        
        # 添加 Header/Footer 标记 (保持不变)
        if header_end > 0:
            ls_predictions.append({
                "from_name": "label", "to_name": "text", "type": "labels",
                "value": { "start": 0, "end": header_end, "text": raw_text[:header_end], "labels": ["HEADER"] },
                "score": 1.0
            })
        if footer_start < len(raw_text):
            ls_predictions.append({
                "from_name": "label", "to_name": "text", "type": "labels",
                "value": { "start": footer_start, "end": len(raw_text), "text": raw_text[footer_start:], "labels": ["FOOTER"] },
                "score": 1.0
            })

        # --- 【关键修改 1】分层切分逻辑 ---
        # 不再全文 replace \n，而是先按行切，再按句切
        # 这样能保留住我们在 clean_rtf 里强制插入的物理换行
        
        sentences = []       # 存储切好的句子文本
        sentence_spans = []  # 存储 (start, end) 相对坐标
        
        cursor = 0
        # splitlines(keepends=True) 保留换行符以便计算坐标
        paragraphs = raw_body.splitlines(keepends=True)
        
        for para in paragraphs:
            # 对该段落进行 NLTK 分句
            # 这里的 para 可能包含结尾的 \n
            para_text_clean = para.strip()
            if not para_text_clean:
                cursor += len(para)
                continue
                
            # span_tokenize 返回的是相对于 para 的坐标
            para_spans = list(nltk.tokenize.PunktSentenceTokenizer().span_tokenize(para))
            
            for start, end in para_spans:
                # 计算相对于 raw_body 的坐标
                global_sent_start = cursor + start
                global_sent_end = cursor + end
                
                sent_text = para[start:end]
                # 清洗一下用于模型预测 (去掉可能存在的首尾空白)
                clean_sent_text = sent_text.strip()
                
                if len(clean_sent_text) > 1:
                    sentences.append(clean_sent_text)
                    sentence_spans.append((global_sent_start, global_sent_end))
            
            cursor += len(para)

        if not sentences: return raw_body.strip(), ls_predictions

        # --- 模型预测 ---
        try:
            results = self.classifier(sentences, truncation=True, max_length=512, batch_size=16)
        except Exception as e:
            print(f"⚠️ AI 预测出错: {e}")
            return raw_body.strip(), ls_predictions

        keep_mask = [True] * len(sentences)
        
        for i, res in enumerate(results):
            sent_text = sentences[i]
            
            # --- 【关键修改 2】优先级逻辑调整 ---
            # 以前：先判断噪音 -> 再判断特赦 (特赦会覆盖噪音判断)
            # 现在：先判断"强噪音" -> 再判断特赦 -> 最后综合判断
            
            is_strong_noise = False # 强噪音 (Photo, Read, URL) - 优先级最高
            is_model_noise = False  # 模型认为的噪音
            is_safe_content = False # 特赦 (长难句, Said)
            
            # A. 规则判断 (黑名单)
            if re.search(r'^(Photo|Image|Source|Figure)\s*(:|by)\s+', sent_text, re.IGNORECASE): is_strong_noise = True
            elif "http" in sent_text or "www." in sent_text: is_strong_noise = True
            elif sent_text.startswith("READ:") or "Click here" in sent_text: is_strong_noise = True
            elif sent_text.isupper() and len(sent_text) < 50: is_strong_noise = True
            # 缩写误判修复 (Gen. / Oct.) - 如果句子太短且以点结尾，可能是误切
            elif len(sent_text) < 5 and sent_text.endswith('.'): 
                # 这种通常是误切的碎片，暂且保留，让它和下一句拼起来 (或者简单地保留)
                # 这里我们选择保留，因为删错了比留错了更严重
                is_safe_content = True 

            # B. 模型判断
            if res['label'] in ["NOISE", "LABEL_0", 0]: 
                is_model_noise = True
            
            # C. 特赦规则 (白名单)
            # 只有在不是"强噪音"的情况下，才允许特赦
            if not is_strong_noise:
                if len(sent_text) > 80: is_safe_content = True
                if re.search(r'\b(said|stated|announced|reported|added|noted|according to)\b', sent_text, re.IGNORECASE): is_safe_content = True
            
            # --- 最终决策 ---
            final_is_noise = False
            
            if is_strong_noise:
                final_is_noise = True # 强规则直接杀
            elif is_safe_content:
                final_is_noise = False # 白名单保释
            elif is_model_noise:
                final_is_noise = True # 模型杀
            
            if final_is_noise:
                keep_mask[i] = False

        # 尾部 Bio 扫尾
        stop_cutting = False
        for i in range(len(sentences) - 1, -1, -1):
            if not keep_mask[i]: continue
            if stop_cutting: break
            
            sent_text = sentences[i]
            is_bio = False
            if re.search(r'^[-–—]\s*[A-Za-z\s\.]+$', sent_text): is_bio = True
            elif "is a writer" in sent_text or "can be reached" in sent_text or "email" in sent_text.lower(): is_bio = True
            
            if is_bio:
                keep_mask[i] = False
            else:
                if len(sent_text) > 30: stop_cutting = True

        # 生成结果
        final_sentences = []
        for i, (start, end) in enumerate(sentence_spans):
            if keep_mask[i]:
                # 保留
                # 这里的 raw_body[start:end] 是带原始格式的(比如可能带换行)
                # 但为了输出好看，我们通常 strip 一下
                final_sentences.append(raw_body[start:end].strip())
            else:
                # 删除 -> 标红
                global_start = body_offset + start
                global_end = body_offset + end
                
                ls_predictions.append({
                    "from_name": "label", 
                    "to_name": "text", 
                    "type": "labels",
                    "value": { 
                        "start": global_start, 
                        "end": global_end, 
                        "text": raw_body[start:end], 
                        "labels": ["NOISE"] 
                    },
                    "score": 0.99
                })
        
        return "\n".join(final_sentences), ls_predictions

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
            if folder not in files_by_folder: files_by_folder[folder] = []
            files_by_folder[folder].append(f)
            
        processed_count = 0
        
        for folder, folder_files in files_by_folder.items():
            ls_diff_tasks = []
            csv_data = []
            
            rel_path = os.path.relpath(folder, input_dir)
            out_folder = os.path.join(output_base_dir, rel_path)
            if not os.path.exists(out_folder): os.makedirs(out_folder)
            
            csv_path = os.path.join(out_folder, "progress_log.csv")
            old_checked = {}
            if os.path.exists(csv_path):
                try:
                    df_old = pd.read_csv(csv_path)
                    for _, row in df_old.iterrows():
                        old_checked[str(row['Filename'])] = row.get('Checked', 'No')
                except: pass

            for rtf_path in folder_files:
                processed_count += 1
                if progress_callback:
                    progress_callback(processed_count, total_files, f"处理: {os.path.basename(rtf_path)}")
                
                raw_text = self.clean_rtf(rtf_path)
                if not raw_text: continue
                
                header_end, footer_start, meta = self.get_structure_indices(raw_text)
                title, date, source = meta
                
                clean_body, ls_labels = self.generate_clean_body_and_labels(raw_text, header_end, footer_start)
                
                file_stem = os.path.splitext(os.path.basename(rtf_path))[0]
                txt_filename = re.sub(r'[\\/*?:"<>|]', "_", file_stem) + ".txt"
                txt_path = os.path.join(out_folder, txt_filename)
                
                final_content = f"<TITLE>{title}</TITLE>\n<DATE>{date}</DATE>\n<SOURCE>{source}</SOURCE>\n<BODY>\n{clean_body}\n</BODY>"
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(final_content)
                
                ls_diff_tasks.append({
                    "data": {"text": raw_text, "file_id": f"{os.path.basename(out_folder)}_{file_stem}"},
                    "predictions": [{"model_version": "v9_final", "result": ls_labels}]
                })
                
                csv_data.append({
                    "Filename": txt_filename,
                    "Title": title,
                    "Date": date,
                    "Source": source,
                    "Checked": old_checked.get(txt_filename, "No")
                })
            
            if csv_data:
                pd.DataFrame(csv_data).to_csv(csv_path, index=False, encoding="utf-8-sig")
            
            if ls_diff_tasks:
                ls_path = os.path.join(out_folder, "diff_check.json")
                with open(ls_path, "w", encoding="utf-8") as f:
                    json.dump(ls_diff_tasks, f, ensure_ascii=False, indent=2)