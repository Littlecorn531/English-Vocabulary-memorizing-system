import random
import os
import platform
import json
import time
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher

# ==================== 1. 内建词库 ====================
DEFAULT_WORD_BANK = {
    "Lesson 1 (核心词与派生)": [
        {"word": "achieve", "meanings": ["取得", "实现", "达到"], "sentences": ["He worked hard to achieve his goals.", "No one can achieve anything without effort."], "hint": "v.", "related_forms": {"achievement": "n."}},
        {"word": "achievement", "meanings": ["成就", "成绩"], "sentences": ["Winning the prize was a great achievement.", "We celebrate your academic achievement."], "hint": "n.", "related_forms": {"achieve": "v."}},
        
        {"word": "brilliant", "meanings": ["聪颖的", "绝妙的", "明亮的"], "sentences": ["She gave a brilliant performance.", "The stars are brilliant tonight."], "hint": "adj.", "related_forms": {"brilliantly": "adv.", "brilliance": "n."}},
        {"word": "brilliantly", "meanings": ["精彩地", "辉煌地"], "sentences": ["The sun shone brilliantly.", "She handled the complex situation brilliantly."], "hint": "adv.", "related_forms": {"brilliant": "adj."}},
        {"word": "brilliance", "meanings": ["才华", "光辉"], "sentences": ["Everyone was amazed by his brilliance.", "The diamond dazzled with brilliant radiance."], "hint": "n.", "related_forms": {"brilliant": "adj."}},
        
        {"word": "challenge", "meanings": ["挑战", "质疑"], "sentences": ["Destiny presents a new challenge to him.", "I challenge his conclusion."], "hint": "n. & v.", "related_forms": {"challenging": "adj."}},
        {"word": "challenging", "meanings": ["具有挑战性的"], "sentences": ["This project is extremely challenging.", "Teaching young kids can be challenging."], "hint": "adj.", "related_forms": {"challenge": "n. & v."}},
    ],
    "Lesson 2 (核心词与派生)": [
        {"word": "determine", "meanings": ["决定", "决心"], "sentences": ["Your attitude determines your altitude.", "We must determine the date for the meeting."], "hint": "v.", "related_forms": {"determination": "n.", "determined": "adj."}},
        {"word": "determination", "meanings": ["决心", "坚定"], "sentences": ["She showed great determination to clear the exam.", "Success requires hard work and determination."], "hint": "n.", "related_forms": {"determine": "v."}},
        {"word": "determined", "meanings": ["下定决心的", "坚定的"], "sentences": ["I am determined to carry out this plan.", "She cast a determined look at her rival."], "hint": "adj.", "related_forms": {"determine": "v."}},
        
        {"word": "enthusiastic", "meanings": ["热情的", "热心的"], "sentences": ["He is enthusiastic about volunteering.", "An enthusiastic crowd welcomed the team."], "hint": "adj.", "related_forms": {"enthusiastically": "adv.", "enthusiasm": "n."}},
        {"word": "enthusiastically", "meanings": ["热情地"], "sentences": ["The audience applauded enthusiastically.", "They support the environment plan enthusiastically."], "hint": "adv.", "related_forms": {"enthiatric": "adj."}},
        {"word": "enthusiasm", "meanings": ["热情", "热忱"], "sentences": ["She is full of enthusiasm for her new job.", "His built-in enthusiasm makes him a good leader."], "hint": "n.", "related_forms": {"enthusiasm": "adj."}}
    ]
}

STATS_FILE = "vocab_stats.json"
LOGS_FILE = "study_logs.json"
CUSTOM_FILE = "custom_lists.json"
CONFIG_FILE = "vocab_config.json"

# ==================== 2. UI 美化模块 (极致对齐版) ====================
class UI:
    HEADER, BLUE, CYAN, GREEN, YELLOW, RED, GRAY, END, BOLD = '\033[95m', '\033[94m', '\033[96m', '\033[92m', '\033[93m', '\033[91m', '\033[90m', '\033[0m', '\033[1m'
    
    @staticmethod
    def clear_screen():
        os.system("cls" if platform.system().lower() == "windows" else "clear")

    @staticmethod
    def get_visual_width(text):
        clean_text = re.sub(r'\033\[[0-9;]*m', '', text)
        width = 0
        for c in clean_text:
            code = ord(c)
            if code in (0xfe0f, 0xfe0e) or code < 32:
                continue
            if 0x2500 <= code <= 0x257f:
                width += 1
            elif code > 127:
                width += 2
            else:
                width += 1
        return width

    @staticmethod
    def box_print(title, text_list, border_color='\033[94m'):
        max_content_len = max(UI.get_visual_width(title), 60)
        for line in text_list:
            max_content_len = max(max_content_len, UI.get_visual_width(line) + 2)
        
        if max_content_len % 2 != 0:
            max_content_len += 1
            
        box_width = max_content_len + 2
        
        print(border_color + "╔" + "═" * box_width + "╗" + UI.END)
        title_len = UI.get_visual_width(title)
        left_pad = (box_width - title_len) // 2
        right_pad = box_width - title_len - left_pad
        print(border_color + "║" + UI.END + " " * left_pad + UI.BOLD + title + UI.END + " " * (right_pad) + border_color + "║" + UI.END)
        print(border_color + "╠" + "═" * box_width + "╣" + UI.END)
        for line in text_list:
            line_len = UI.get_visual_width(line)
            right_pad = box_width - line_len - 2
            print(border_color + "║" + UI.END + " " + line + " " * (right_pad + 1) + border_color + "║" + UI.END)
        print(border_color + "╚" + "═" * box_width + "╝" + UI.END)

# ==================== 3. 核心数据管理中心 (完整方法绑定) ====================
class DataManager:
    def __init__(self):
        self.stats = {}    
        self.logs = []     
        self.custom_bank = {} 
        self.sentence_counts = {} 
        self.last_selected_keys = []  
        self.load_all()

    def load_all(self):
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    if isinstance(data, dict) and "stats" in data:
                        self.stats = data.get("stats", {})
                        self.sentence_counts = data.get("sentence_counts", {})
                    else:
                        self.stats = data
                        self.sentence_counts = {}
                except Exception:
                    self.stats = {}
                    self.sentence_counts = {}
            
            modified = False
            for word, s in self.stats.items():
                if "interval" not in s:
                    s["interval"] = 0
                    modified = True
                if "ease" not in s:
                    s["ease"] = 2.5
                    modified = True
                if "next_date" not in s:
                    s["next_date"] = datetime.now().isoformat()
                    modified = True
            if modified:
                self.save_all()

        if os.path.exists(LOGS_FILE):
            with open(LOGS_FILE, 'r', encoding='utf-8') as f:
                self.logs = json.load(f)
        if os.path.exists(CUSTOM_FILE):
            with open(CUSTOM_FILE, 'r', encoding='utf-8') as f:
                self.custom_bank = json.load(f)
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                self.last_selected_keys = json.load(f)

    def save_all(self):
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"stats": self.stats, "sentence_counts": self.sentence_counts}, f, ensure_ascii=False, indent=4)
        with open(LOGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.logs, f, ensure_ascii=False, indent=4)
        with open(CUSTOM_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.custom_bank, f, ensure_ascii=False, indent=4)

    def save_config(self, keys):
        self.last_selected_keys = keys
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(keys, f, ensure_ascii=False, indent=4)

    def log_word_attempt(self, word, mode_type, is_correct):
        if word not in self.stats:
            self.stats[word] = {
                "meaning_errors": 0, "spelling_errors": 0, "test_count": 0,
                "interval": 0, "ease": 2.5, "next_date": datetime.now().isoformat()
            }
        
        s = self.stats[word]
        s["test_count"] = s.get("test_count", 0) + 1
        
        if is_correct:
            if s.get("interval", 0) == 0: s["interval"] = 1
            elif s["interval"] == 1: s["interval"] = 6
            else: s["interval"] = round(s["interval"] * s.get("ease", 2.5))
            s["ease"] = max(1.3, s.get("ease", 2.5) + 0.1)
        else:
            if mode_type == "meaning":
                s["meaning_errors"] = s.get("meaning_errors", 0) + 1
            elif mode_type == "spelling":
                s["spelling_errors"] = s.get("spelling_errors", 0) + 1
            s["interval"] = 1  
            s["ease"] = max(1.3, s.get("ease", 2.5) - 0.2)
            
        s["next_date"] = (datetime.now() + timedelta(days=s["interval"])).isoformat()
        self.save_all()

    def log_sentence_exam(self, sentence):
        self.sentence_counts[sentence] = self.sentence_counts.get(sentence, 0) + 1
        self.save_all()

    def add_study_log(self, mode_name, total, errors, duration_secs):
        mins, secs = divmod(int(duration_secs), 60)
        time_str = f"{mins}分{secs}秒" if mins > 0 else f"{secs}秒"
        log_entry = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "mode": mode_name,
            "total": total,
            "errors": errors,
            "duration": time_str,
            "raw_duration": int(duration_secs) # 记录原始秒数用于高维数据统计
        }
        self.logs.append(log_entry)
        self.save_all()

    def get_word_weight(self, word):
        stat = self.stats.get(word, {"meaning_errors": 0, "spelling_errors": 0, "test_count": 0})
        total_errors = stat.get("meaning_errors", 0) + stat.get("spelling_errors", 0)
        test_count = stat.get("test_count", 0)
        
        now = datetime.now().isoformat()
        due_bonus = 2.0 if stat.get("next_date", now) <= now else 1.0
        
        base_weight = 10 + (total_errors * 15) / (test_count + 1) + max(0, 10 - test_count)
        return base_weight * due_bonus

    def clear_all_data(self):
        self.stats = {}
        self.logs = []
        self.custom_bank = {}
        self.sentence_counts = {}
        self.last_selected_keys = []
        for file in [STATS_FILE, LOGS_FILE, CUSTOM_FILE, CONFIG_FILE]:
            if os.path.exists(file):
                try: os.remove(file)
                except Exception: pass
        return True

dm = DataManager()

# ==================== 4. 辅助智能算法与工具 ====================
def calculate_similarity(w1, w2):
    return SequenceMatcher(None, w1.lower(), w2.lower()).ratio()

def check_pos_match(p1, p2):
    set1 = set(re.findall(r'[a-z]+\.', p1.lower()))
    set2 = set(re.findall(r'[a-z]+\.', p2.lower()))
    return not set1.isdisjoint(set2)

def smart_replace(sentence, word, placeholder):
    """带变体识别及防空缺退化机制的整词正则替换"""
    pattern = re.compile(rf'\b{word}(s|es|ed|ing|d)?\b', re.IGNORECASE)
    def repl_func(match):
        orig = match.group(0)
        if orig.istitle(): return placeholder.capitalize()
        if orig.isupper(): return placeholder.upper()
        return placeholder
    
    result = pattern.sub(repl_func, sentence)
    if result == sentence:
        return sentence + f" ({placeholder})"
    return result

def fuzzy_check(user_input, target):
    return calculate_similarity(user_input, target) >= 0.85

def generate_smart_distractors_with_sources(target_item, full_pool):
    """生成带有原词追溯源的智能干扰项数据"""
    target_word = target_item['word']
    target_hint = target_item.get('hint', '')
    target_meanings = set(target_item['meanings'])
    
    candidates = []
    seen_words = set([target_word.lower()])
    
    for item in full_pool:
        w_lower = item['word'].lower()
        if w_lower in seen_words: continue
        if not target_meanings.isdisjoint(set(item['meanings'])): continue
        candidates.append(item)
        seen_words.add(w_lower)

    scored_candidates = []
    for item in candidates:
        sim_score = calculate_similarity(target_word, item['word'])
        pos_match = 1 if check_pos_match(item.get('hint', ''), target_hint) else 0
        final_score = (sim_score * 0.7) + (pos_match * 0.3)  
        scored_candidates.append((final_score, item))
        
    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    distractors_data = []
    seen_meanings = set()
    for _, item in scored_candidates:
        chosen_m = random.choice(item['meanings'])
        if chosen_m not in seen_meanings:
            distractors_data.append((chosen_m, item['word']))
            seen_meanings.add(chosen_m)
        if len(distractors_data) == 3: break
            
    while len(distractors_data) < 3 and full_pool:
        random_item = random.choice(full_pool)
        chosen_m = random.choice(random_item['meanings'])
        if chosen_m not in seen_meanings:
            distractors_data.append((chosen_m, random_item['word']))
            seen_meanings.add(chosen_m)
    return distractors_data

# ==================== 5. 智能合并导入器 ====================
def import_local_file():
    UI.clear_screen()
    content = [
        "📥 智能自适应词汇导入系统 📥",
        "",
        "系统已支持双格式自动识别：",
        " 1. [JSON 格式]：直接输入完整 JSON 词库路径 (自动无损合并)",
        " 2. [TXT  格式]：输入遵循五段式规范的文本路径",
        "    格式 -> 单词,中文释义,完整例句,当前词性,原型词:目标词性",
    ]
    UI.box_print(" 📥 导入本地外部词汇表 ", content, UI.CYAN)
    path = input(f"\n✍️  请输入要导入的文件路径 (如 ./my_vocab.json 或 ./vocab.txt, 输入 q 退出): ").strip()
    
    if path.lower() == 'q' or path == ' ': return
    if not os.path.exists(path):
        input(f"\n{UI.RED}❌ 文件未找到，导入失败。按回车返回...{UI.END}")
        return
    
    try:
        is_json = False
        with open(path, 'r', encoding='utf-8') as f:
            sample = f.read(150).strip()
            if sample.startswith("{") or path.lower().endswith(".json"):
                is_json = True
                
        if is_json:
            with open(path, 'r', encoding='utf-8') as f:
                new_data = json.load(f)
            
            imported_count = 0
            for section, words in new_data.items():
                if section not in dm.custom_bank:
                    dm.custom_bank[section] = []
                for word_item in words:
                    if not any(item['word'] == word_item['word'] for item in dm.custom_bank[section]):
                        dm.custom_bank[section].append(word_item)
                        imported_count += 1
            if imported_count > 0:
                dm.save_all()
                success_info = [
                    f"✔ 成功安全导入 JSON 词条共计: {UI.GREEN}{imported_count}{UI.END} 个",
                    "🔗 词形转换引擎已完成全自适应网状双向绑定！"
                ]
                UI.box_print(" 🎉 JSON 导入成功 🎉 ", success_info, UI.GREEN)
            else:
                print(f"\n{UI.YELLOW}⚠ 未检测到可添加的新词条（可能已全部存在）。{UI.END}")
            input(f"\n{UI.GRAY}按回车键返回主菜单...{UI.END}")
            return

        current_section = "外部导入词表"
        imported_count = 0
        relations_to_wire = []  
        
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line_str = line.strip()
                if not line_str or line_str.startswith("#"):
                    if "===" in line_str or "---" in line_str:
                        clean_sec = line_str.replace("#", "").replace("=", "").replace("-", "").strip()
                        if clean_sec: current_section = clean_sec
                    continue
                
                parts = line_str.split(',')
                if len(parts) >= 4:
                    word = parts[0].strip()
                    meanings = [m.strip() for m in parts[1].strip().split('/') if m.strip()]
                    sentences = [s.strip() for s in parts[2].strip().split('|') if s.strip()]
                    pos_hint = parts[3].strip()
                    
                    related_dict = {}
                    if len(parts) >= 5 and parts[4].strip():
                        rel_info = parts[4].strip()
                        if ":" in rel_info:
                            base_word, target_pos = rel_info.split(':', 1)
                            related_dict[base_word.strip()] = target_pos.strip()
                            relations_to_wire.append((current_section, word, base_word.strip(), target_pos.strip()))
                    
                    word_item = {
                        "word": word, "meanings": meanings, "sentences": sentences, "hint": pos_hint, "related_forms": related_dict
                    }
                    
                    if current_section not in dm.custom_bank:
                        dm.custom_bank[current_section] = []
                        
                    if not any(item['word'] == word for item in dm.custom_bank[current_section]):
                        dm.custom_bank[current_section].append(word_item)
                        imported_count += 1

        # 构建双向网状互联
        for sec, p_word, b_word, pos in relations_to_wire:
            for item in dm.custom_bank[sec]:
                if item['word'] == b_word:
                    item['related_forms'][p_word] = pos
                if item['word'] == p_word:
                    base_items = [i for i in dm.custom_bank[sec] if i['word'] == b_word]
                    base_pos = base_items[0]['hint'] if base_items else "v."
                    item['related_forms'][b_word] = base_pos

        if imported_count > 0:
            dm.save_all()
            success_info = [
                f"✔ 成功安全导入 TXT 词条共计: {UI.GREEN}{imported_count}{UI.END} 个",
                f"📂 已成功归档至自选区小节: 【 {current_section} 】"
            ]
            UI.box_print(" 🎉 TXT 导入成功 🎉 ", success_info, UI.GREEN)
        else:
            input(f"\n{UI.YELLOW}⚠ 未能从文件中解析出符合五段式规范的新单词，请检查格式。{UI.END}")
    except Exception as e:
        input(f"\n{UI.RED}❌ 读取或解析过程发生异常: {e}。按回车返回...{UI.END}")

# ==================== 6. 词库选择与取反控制 ====================
def select_word_pool():
    full_bank = {}
    full_bank.update(DEFAULT_WORD_BANK)
    full_bank.update(dm.custom_bank)
    keys = list(full_bank.keys())
    
    selected_set = set(k for k in dm.last_selected_keys if k in keys)
    if not selected_set:
        selected_set = set(keys)
        
    while True:
        UI.clear_screen()
        has_history = len(selected_set) > 0
        
        text_lines = []
        for idx, key in enumerate(keys, 1):
            source_tag = f"{UI.YELLOW}[自选]{UI.END}" if key in dm.custom_bank else f"{UI.GREEN}[课本]{UI.END}"
            status_tag = f"{UI.GREEN}[X]{UI.END}" if key in selected_set else "[ ]"
            text_lines.append(f" {status_tag} [{idx}] {source_tag} {key} ({len(full_bank[key])} 词)")
        
        text_lines.append("")
        text_lines.append(f" [A] 一键全选        [N] 一键全不选")
        text_lines.append(f" * 直接敲 [回车键] 即可应用并保存当前勾选状态并退出")
        text_lines.append(f" * 输入序号对状态取反 (如 '1 3' 切换选择状态)")
        text_lines.append(f" * 支持区间取反 (如输入 '[1,3]' 切换选择状态, 输入 q 退出)")
        text_lines.append(f" * 输入 'i' 导入新文件。")
        
        UI.box_print(" 📚 智能自适应词库多选面板 ", text_lines, UI.BLUE)
        choice = input(f"\n✍️  请做出选择: ").strip()
        
        if choice.lower() == 'q' or choice == ' ':
            break
            
        if choice == '':
            if not selected_set:
                print(f"\n{UI.RED}❌ 激活词池不能为空，请至少保留一个勾选的词表！{UI.END}")
                time.sleep(1.5)
                continue
            
            selected_list = [k for k in keys if k in selected_set]
            dm.save_config(selected_list)
            pool = []
            for k in selected_list: pool.extend(full_bank[k])
            display_name = "+".join(selected_list) if len(selected_list) <= 2 else f"{selected_list[0]}等{len(selected_list)}个词表"
            return pool, display_name
            
        if choice.lower() == 'i':
            import_local_file()
            continue
            
        if choice.lower() == 'a':
            selected_set = set(keys)
            continue
            
        if choice.lower() == 'n':
            selected_set.clear()
            continue
            
        try:
            toggled_indices = set()
            
            ranges = re.findall(r'\[\s*(\d+)\s*,\s*(\d+)\s*\]', choice)
            for l_str, r_str in ranges:
                l, r = int(l_str), int(r_str)
                if l > r: l, r = r, l  
                for i in range(l, r + 1):
                    toggled_indices.add(i - 1)
            
            clean_choice = re.sub(r'\[\s*\d+\s*,\s*\d+\s*\]', ' ', choice)
            for token in clean_choice.split():
                if token.isdigit():
                    toggled_indices.add(int(token) - 1)
            
            valid_indices = [i for i in toggled_indices if 0 <= i < len(keys)]
            if not valid_indices:
                print(f"\n{UI.RED}❌ 未检测到合法的词表序号或区间，请重试。{UI.END}")
                time.sleep(1.2)
                continue
                
            for idx in valid_indices:
                key_to_toggle = keys[idx]
                if key_to_toggle in selected_set:
                    selected_set.remove(key_to_toggle)
                else:
                    selected_set.add(key_to_toggle)
                    
            dm.save_config(list(selected_set))  
            
        except Exception:
            print(f"\n{UI.RED}❌ 输入格式解析失败，请重试。{UI.END}")
            time.sleep(1.2)

def get_smart_word(word_pool, exclude_word=None):
    valid_pool = [w for w in word_pool if w['word'] != exclude_word] if exclude_word else word_pool
    if not valid_pool: return random.choice(word_pool)
    weights = [dm.get_word_weight(w['word']) for w in valid_pool]
    return random.choices(valid_pool, weights=weights, k=1)[0]

def view_current_pool_paginated(word_pool, pool_name):
    UI.clear_screen()
    if not word_pool:
        input(f"\n{UI.RED}⚠ 当前词表为空。按回车返回...{UI.END}")
        return
        
    page_size = 15
    total = len(word_pool)
    for i in range(0, total, page_size):
        UI.clear_screen()
        chunk = word_pool[i : i + page_size]
        
        lines = [f"{UI.BOLD}{'单词 (Word)':<15} | {'词性':<5} | 关联核心 / 中文释义{UI.END}", "-" * 65]
        for idx, item in enumerate(chunk, i + 1):
            meanings_str = "/".join(item['meanings'])
            related_str = f"🔗({list(item['related_forms'].keys())[0]}) " if item.get('related_forms') else ""
            lines.append(f"[{idx:02d}] {item['word']:<12} | {item.get('hint', 'n.'):<5} | {related_str}{meanings_str}")
        
        lines.append("")
        lines.append(f"--- 第 {i//page_size + 1} 页 / 共 {-(total//-page_size)} 页 (直接敲回车翻页，输入 q 或空格退出) ---")
        UI.box_print(f" 📖 预览：{pool_name} ", lines, UI.CYAN)
        
        cmd = input().strip().lower()
        if cmd == 'q' or cmd == ' ' or cmd == '':
            if cmd == 'q' or cmd == ' ':
                break

# ==================== 7. 核心测试 Session 引擎 ====================
def run_quiz_session(word_pool, mode_choice):
    if not word_pool:
        input(f"\n{UI.RED}❌ 激活词表为空！请先去选项 [7] 配置或加载单词。{UI.END}")
        return
        
    UI.clear_screen()
    try: total_ques = int(input(f"🔢 你期望本次练习完成多少道题？(输入 q 退出): ").strip())
    except ValueError: total_ques = 5
        
    error_cnt = 0
    actual_mode_name = "形似字义辨析" if mode_choice=='1' else "完形空缺拼写" if mode_choice=='2' else "语法填空词形变化" if mode_choice=='3' else "综合挑战"
    input_mapping = {'A': 0, '1': 0, 'B': 1, '2': 1, 'C': 2, '3': 2, 'D': 3, '4': 3}
    
    start_time = time.perf_counter()
    exit_session = False
    
    for step in range(1, total_ques + 1):
        if exit_session: break
        current_sub_mode = mode_choice if mode_choice in ['1','2','3'] else random.choice(['1', '2', '3'])
        
        if current_sub_mode == '3':
            has_relations = [w for w in word_pool if w.get('related_forms')]
            target = get_smart_word(has_relations) if has_relations and random.random() < 0.9 else get_smart_word(word_pool)
        else:
            target = get_smart_word(word_pool)
            
        UI.clear_screen()
        print(f"{UI.GRAY}第 {step} / {total_ques} 题 进行中... (当前错误数: {error_cnt}, 输入 q 或空格退出){UI.END}")
        
        if current_sub_mode == '1':  
            correct_meaning_plain = random.choice(target['meanings'])
            
            # 🌟 新功能：使用配有源词映射的干扰项生成器
            options_data = [(correct_meaning_plain, target['word'])]
            wrong_data = generate_smart_distractors_with_sources(target, word_pool)
            options_data.extend(wrong_data)
            random.shuffle(options_data)
            
            options = [item[0] for item in options_data]
            labels_display = ['A (1)', 'B (2)', 'C (3)', 'D (4)']
            
            box = [
                f"请在库内动态匹配出的干扰项中精准辨析：", "",
                f"   单词: {UI.YELLOW}{UI.BOLD}{target['word']}{UI.END}  (提示词性: {target.get('hint', 'n.')})", ""
            ]
            for l, o in zip(labels_display, options): box.append(f" 【 {UI.CYAN}{l}{UI.END} 】 {o}")
            UI.box_print(" 📝 核心义项深度辨析 ", box, UI.CYAN)
            ans = input("\n🤔 你的选择 (A-D 或 1-4, 输入 q 或空格退出): ").strip().upper()
            
            if ans == 'Q' or ans == ' ':
                exit_session = True
                break
                
            is_ok = (ans in input_mapping and options[input_mapping[ans]] == correct_meaning_plain)
            dm.log_word_attempt(target['word'], "meaning", is_ok)
            target_word_correct = target['word']
            
            if is_ok:
                print(f"\n{UI.GREEN}✔ 完全正确！思维非常清晰！{UI.END}")
            else:
                print(f"\n{UI.RED}❌ 掉进陷阱啦！{UI.END} 正确答案为: {UI.GREEN}{target_word_correct}{UI.END} [{target.get('hint','n.')}] -> {', '.join(target['meanings'])}")
                # 🌟 新功能：在答错时显示各选项对应的单词解析
                print(f"   {UI.YELLOW}各选项对应原词解析：{UI.END}")
                for idx_opt, item in enumerate(options_data):
                    lbl = ['A', 'B', 'C', 'D'][idx_opt]
                    opt_meaning, opt_word = item
                    src_item = next((w for w in word_pool if w['word'] == opt_word), None)
                    src_pos = src_item.get('hint', 'n.') if src_item else 'n.'
                    print(f"     - {lbl}: {opt_meaning} -> {UI.CYAN}{opt_word}{UI.END} ({src_pos})")
            
        elif current_sub_mode == '2':  
            s_list = target.get("sentences", ["This is a sentence for " + target['word']])
            s_list_sorted = sorted(s_list, key=lambda s: dm.sentence_counts.get(s, 0))
            chosen_sentence = s_list_sorted[0]
            dm.log_sentence_exam(chosen_sentence)
            
            w_len = len(target['word'])
            blank = target['word'][0] + "_" * (w_len - 1)
            blank_s = smart_replace(chosen_sentence, target['word'], blank)
            
            box = [
                f"请根据首字母和字数提示，补全语境完形空缺处的单词：", "",
                f"  {blank_s} ({w_len} 个字母)", "",
                f"  * 如果一时想不起来，可以输入 'q' 获取中文意思提示"
            ]
            UI.box_print(" 🔤 完形空缺拼写 ", box, UI.HEADER)
            
            ans = input("\n✍️ 请输入完整单词 (输入 q 或空格退出): ").strip().lower()
            if ans == 'q' or ans == ' ':
                exit_session = True
                break
            if ans == 'q':
                print(f"💡 【中文提示】: {UI.YELLOW}{'/'.join(target['meanings'])}{UI.END}")
                ans = input("✍️ 再次尝试输入完整单词: ").strip().lower()
                
            is_ok = (ans == target['word'].lower())
            
            if not is_ok and fuzzy_check(ans, target['word']):
                print(f"\n{UI.YELLOW}⚠️ 很接近了！拼写正确答案是: {UI.BOLD}{target['word']}{UI.END}")
                time.sleep(1.2)
                
            dm.log_word_attempt(target['word'], "spelling", is_ok)
            target_word_correct = target['word']
            
            if is_ok:
                print(f"\n{UI.GREEN}✔ 完全正确！思维非常清晰！{UI.END}")
            else:
                print(f"\n{UI.RED}❌ 掉进陷阱啦！{UI.END} 正确答案为: {UI.GREEN}{target_word_correct}{UI.END} [{target.get('hint','n.')}] -> {', '.join(target['meanings'])}")
            
        else:  
            relations = target.get("related_forms", {})
            if not relations:
                base_word_prompt = target['word']
                req_pos = target.get('hint', 'n.')
                target_word_correct = target['word']
            else:
                base_word_prompt, target_pos_info = random.choice(list(relations.items()))
                target_word_correct = target['word']
                
                matched_targets = [w for w in word_pool if w['word'] == target_word_correct]
                req_pos = matched_targets[0]['hint'] if matched_targets else target_pos_info
                
            s_list = target.get("sentences", ["It requires morphological transformation."])
            chosen_sentence = random.choice(s_list)
            blank_s = smart_replace(chosen_sentence, target_word_correct, "_______")
            
            box = [
                f"语法填空：根据独立单词关联网络，写出括号内提示词的正确变化：", "",
                f"  {blank_s}  ( 给定提示词: {UI.BOLD}{base_word_prompt}{UI.END} -> {req_pos} )"
            ]
            UI.box_print(" ✨ 语法填空：关联词形变化突破 ", box, UI.YELLOW)
            ans = input("\n✍️ 填写正确词形 (输入 q 或空格退出): ").strip().lower()
            if ans == 'q' or ans == ' ':
                exit_session = True
                break
                
            is_ok = (ans == target_word_correct.lower())
            dm.log_word_attempt(target_word_correct, "spelling", is_ok)
            
            if is_ok:
                print(f"\n{UI.GREEN}✔ 完全正确！思维非常清晰！{UI.END}")
            else:
                print(f"\n{UI.RED}❌ 掉进陷阱啦！{UI.END} 正确答案为: {UI.GREEN}{target_word_correct}{UI.END} [{target.get('hint','n.')}] -> {', '.join(target['meanings'])}")
            
        print(f"\n{UI.GRAY}按回车键进入下一题... (输入 q 或空格退出){UI.END}")
        next_cmd = input().strip().lower()
        if next_cmd == 'q' or next_cmd == ' ':
            exit_session = True
            break
        
    end_time = time.perf_counter()
    duration_secs = end_time - start_time
    dm.add_study_log(actual_mode_name, total_ques, error_cnt, duration_secs)
    
    UI.clear_screen()
    report = [
        f" 本轮自适应深度挑战已圆满结束！", "",
        f"  练习统计情况如下：",
        f"   - 总题数量: {total_ques} 道", 
        f"   - 答错数量: {UI.RED}{error_cnt}{UI.END} 道",
        f"   - 本轮用时: {UI.YELLOW}{time.strftime('%M分%S秒', time.gmtime(duration_secs))}{UI.END}", 
        f"   - 终结正确率: {UI.GREEN}{((total_ques-error_cnt)/total_ques)*100:.1f}%{UI.END}"
    ]
    UI.box_print(" 📊 本轮深度战报（已存本地） ", report, UI.GREEN)
    input(f"\n{UI.GRAY}按回车键返回主菜单...{UI.END}")

# ==================== 8. 数据反馈与清理中心 (含弱项 MD 导出与总数据日志) ====================
def show_data_center():
    while True:
        UI.clear_screen()
        box = [
            f" 1. 查看 【每个单词的高频错误排行】",
            f" 2. 查看 【历次背词用时与完整统计日志】 (支持多页查看)",
            f" 3. 📉 导出个人专属 【高频弱项复盘清单】 (Markdown 格式)",
            f" 4. 🚨 物理清空本地所有历史数据 (还原系统)",
            f" 0. 返回主菜单"
        ]
        UI.box_print(" 📈 数据反馈与清理中心 ", box, UI.YELLOW)
        c = input("\n👉 请输入查看或操控编号: ").strip()
        
        if c.lower() == 'q' or c == ' ' or c == '0':
            break
            
        if c == '1':
            UI.clear_screen()
            sorted_stats = sorted(dm.stats.items(), key=lambda x: (x[1].get("meaning_errors", 0) + x[1].get("spelling_errors", 0)), reverse=True)
            lines = [f"{UI.BOLD}单词{UI.END} | {UI.RED}释义错{UI.END} | {UI.RED}拼写错{UI.END} | {UI.YELLOW}{UI.BOLD}总错误{UI.END} | 下次复习安排"]
            lines.append("-" * 65)
            for w, s in sorted_stats[:15]: 
                total_errors = s.get("meaning_errors", 0) + s.get("spelling_errors", 0)
                next_date_show = s.get("next_date", "")[:10] if s.get("interval", 0) > 0 else "未激活"
                lines.append(f"{w:<12} | {s.get('meaning_errors',0):^6} | {s.get('spelling_errors',0):^6} | {total_errors:^6} | {next_date_show}")
            UI.box_print(" 🔥 易错核心词Top 15 ", lines, UI.RED)
            input("\n按回车继续...")
            
        elif c == '2':
            # 🌟 新功能：完整日志分页显示 + 顶部高维累计数据统计
            def get_seconds(log_item):
                if "raw_duration" in log_item:
                    return log_item["raw_duration"]
                # 兼容旧版本字符串格式解析
                dur_str = log_item.get("duration", "0秒")
                match_dur = re.match(r'(?:(\d+)分)?(\d+)秒', dur_str)
                if match_dur:
                    m_val = int(match_dur.group(1)) if match_dur.group(1) else 0
                    s_val = int(match_dur.group(2))
                    return m_val * 60 + s_val
                return 0
                
            total_sessions = len(dm.logs)
            total_questions = sum(l.get("total", 0) for l in dm.logs)
            total_errors = sum(l.get("errors", 0) for l in dm.logs)
            total_seconds = sum(get_seconds(l) for l in dm.logs)
            
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            total_time_str = f"{hours}小时{minutes}分{seconds}秒" if hours > 0 else f"{minutes}分{seconds}秒"
            
            header_summary = [
                f"{UI.BOLD}📊 历史累计学习统计数据：{UI.END}",
                f"   - 总练习次数: {UI.GREEN}{total_sessions}{UI.END} 次",
                f"   - 总刷题数量: {UI.GREEN}{total_questions}{UI.END} 道 (做错 {UI.RED}{total_errors}{UI.END} 道)",
                f"   - 总练习用时: {UI.YELLOW}{total_time_str}{UI.END}",
                "-" * 55
            ]
            
            page_size = 10
            total_logs = len(dm.logs)
            exit_log_view = False
            for i in range(0, total_logs, page_size):
                if exit_log_view: break
                UI.clear_screen()
                chunk = dm.logs[i:i+page_size]
                lines = list(header_summary)
                for idx, l in enumerate(chunk, i + 1):
                    dur = l.get('duration', '未知耗时')
                    lines.append(f"[{idx:02d}] {l['time']} | {l['mode']} | 共{l['total']}题 | 错{UI.RED}{l['errors']}{UI.END}题 | 耗时:{UI.YELLOW}{dur}{UI.END}")
                
                lines.append("")
                lines.append(f"--- 第 {i//page_size + 1} 页 / 共 {-(total_logs//-page_size)} 页 (回车下翻, 输入 q 或空格退出) ---")
                UI.box_print(" 🗓️ 完整历史背词日志 ", lines, UI.BLUE)
                
                cmd = input().strip().lower()
                if cmd == 'q' or cmd == ' ':
                    exit_log_view = True
                    break
            else:
                input(f"\n{UI.GRAY}已展示全部日志。按回车返回...{UI.END}")
            
        elif c == '3':
            filename = "Weak_Words_Report.md"
            try:
                with open(filename, "w", encoding='utf-8') as f:
                    f.write("# 📓 英语弱项高频错词复盘清单\n\n")
                    f.write("| 单词 | 义项错误 | 拼写错误 | 记忆间隔(天) | 下次建议复习日期 |\n")
                    f.write("| :--- | :---: | :---: | :---: | :--- |\n")
                    for w, s in dm.stats.items():
                        m_err = s.get("meaning_errors", 0)
                        s_err = s.get("spelling_errors", 0)
                        if (m_err + s_err) > 0:
                            f.write(f"| **{w}** | {m_err} | {s_err} | {s.get('interval', 0)} 天 | {s.get('next_date', '')[:10]} |\n")
                input(f"\n{UI.GREEN}✔ 报告成功导出至: {filename}。{UI.END}\n按回车继续...")
            except Exception as e:
                input(f"\n{UI.RED}❌ 导出失败: {e}。按回车继续...{UI.END}")
                
        elif c == '4':
            UI.clear_screen()
            warn_box = [
                " 警告：该操作将执行【不可逆】的全面大扫除！",
                "",
                "  将彻底抹除本地的：",
                "   - 历史答题错题本排行与艾宾浩斯参数",
                "   - 每次练习耗时持久化日志",
                "   - 外部自定义导入的词表",
                "   - 上次选中的词库记忆配置",
                "",
                f" 确定要清空并初始化背词系统吗？(YES/NO)"
            ]
            UI.box_print(" 🚨 物理清空本地所有数据 ", warn_box, UI.RED)
            double_check = input("\n👉 请输入完整的 'YES' 确认执行: ").strip()
            if double_check == "YES":
                dm.clear_all_data()
                print(f"\n{UI.GREEN}所有本地数据及配置已完全清除！请重启系统。{UI.END}")
                input("\n按回车退出系统...")
                exit()
            else:
                input(f"\n{UI.GRAY}已取消重置操作。按回车继续...{UI.END}")

def run_wrong_words_reprint():
    wrong_words = [w for w, s in dm.stats.items() if (s.get("meaning_errors", 0) + s.get("spelling_errors", 0)) > 0]
    if not wrong_words:
        UI.clear_screen()
        input(f"\n{UI.GREEN}✨ 恭喜！目前本地记录中没有任何错题。按回车返回...{UI.END}")
        return
    full_bank = {}
    full_bank.update(DEFAULT_WORD_BANK)
    full_bank.update(dm.custom_bank)
    pool = []
    for k in full_bank:
        for w in full_bank[k]:
            if w['word'] in wrong_words: pool.append(w)
    if not pool:
        input(f"\n{UI.GRAY}错题库对应的源词表已被卸载或未加载。按回车返回...{UI.END}")
        return
    print(f"\n🔔 成功从历史记录打捞出 {len(pool)} 个错词！")
    run_quiz_session(pool, "mix")

# ==================== 9. 主控入口循环 ====================
def main():
    if platform.system().lower() == "windows": os.system("") 
    
    while True:
        full_bank = {}
        full_bank.update(DEFAULT_WORD_BANK)
        full_bank.update(dm.custom_bank)
        
        current_pool = []
        selected_keys = []
        if dm.last_selected_keys:
            selected_keys = [k for k in dm.last_selected_keys if k in full_bank]
            
        if selected_keys:
            for k in selected_keys: current_pool.extend(full_bank[k])
            pool_name = "+".join(selected_keys) if len(selected_keys) <= 2 else f"{selected_keys[0]}等{len(selected_keys)}个词表"
        else:
            for l in full_bank.values(): current_pool.extend(l)
            pool_name = "所有融合激活词表" if dm.custom_bank else "所有课本词 (含派生独立词)"
            
        now_time_iso = datetime.now().isoformat()
        due_count = sum(1 for w in current_pool if dm.stats.get(w['word'], {}).get('next_date', now_time_iso) <= now_time_iso)
            
        UI.clear_screen()
        status = [
            f" 当前词库范围: {UI.YELLOW}{pool_name}{UI.END}",
            f" 可选单词基数: {UI.GREEN}{len(current_pool)} 个词{UI.END} | {UI.CYAN}今日到期需复习: {due_count} 词{UI.END}"
        ]
        UI.box_print(" ⚡ 高中英语智能自适应系统 v6.0 ⚡ ", status, UI.GREEN)
        
        menu = [
            f"  [1] 看词辨义 (库内动态匹配干扰 + 词性显示)",
            f"  [2] 完形空缺拼写 (首字母+字数限制，按q提示意)",
            f"  [3] 语法填空：词形变化突破 (独立派生词双向互联考查)",
            f"  [4] 🔀 高强度随机混合多模挑战",
            f"  -------------------------------------",
            f"  [5] 🚨 历史错题重现大扫除",
            f"  [6] 📈 数据中心 (查看错词排行、导出弱项清单、全面重置)",
            f"  [7] 🔄 选择子词表 / 智能导入 (支持 A/N/Enter 一键恢复)",
            f"  [8] 🔍 查看当前激活词表一览 (分页预览模式)",
            f"  [0] ❌ 退出背词系统"
        ]
        UI.box_print(" 核心操控台 ", menu, UI.BLUE)
        
        mode = input(f"\n👉 请输入操作编号: ").strip()
        if mode == '0' or mode.lower() == 'q' or mode == ' ':
            UI.clear_screen()
            print(f"\n{UI.GREEN}✨ 进度与词库记忆已自动同步。智能词学网络已关闭，祝你学习进步，高考加油！ 👋{UI.END}\n")
            break
            
        if mode in ['1', '2', '3', '4']: run_quiz_session(current_pool, mode)
        elif mode == '5': run_wrong_words_reprint()
        elif mode == '6': show_data_center()
        elif mode == '7': current_pool, pool_name = select_word_pool()
        elif mode == '8': view_current_pool_paginated(current_pool, pool_name)

if __name__ == "__main__":
    main()
