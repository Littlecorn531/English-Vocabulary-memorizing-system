import random
import os
import platform
import json
import time
import re
import webbrowser
from datetime import datetime, timedelta
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server
from difflib import SequenceMatcher
from threading import Thread

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
    ]
}

STATS_FILE = "vocab_stats.json"
LOGS_FILE = "study_logs.json"
CUSTOM_FILE = "custom_lists.json"
CONFIG_FILE = "vocab_config.json"

# ==================== 2. 数据管理中心 ====================
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
            "raw_duration": int(duration_secs)
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

# ==================== 3. 自适应辅助函数 ====================
def calculate_similarity(w1, w2):
    return SequenceMatcher(None, w1.lower(), w2.lower()).ratio()

def check_pos_match(p1, p2):
    set1 = set(re.findall(r'[a-z]+\.', p1.lower()))
    set2 = set(re.findall(r'[a-z]+\.', p2.lower()))
    return not set1.isdisjoint(set2)

def fuzzy_check(user_input, target):
    return calculate_similarity(user_input, target) >= 0.85

def generate_smart_distractors_with_sources(target_item, full_pool):
    target_word = target_item['word']
    target_hint = target_item.get('hint', '')
    target_meanings = set(target_item['meanings'])
    candidates = []
    seen_words = {target_word.lower()}
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

# ==================== 4. 会话测试状态机 ====================
class SessionState:
    def __init__(self):
        self.current_pool = []
        self.pool_name = "默认未选择"
        self.quiz_words = []
        self.current_index = 0
        self.error_count = 0
        self.answered_count = 0  
        self.start_time = 0
        self.current_mode = "1"
        self.current_word = None
        self.options_data = []
        self.expected_answer = "" 

ss = SessionState()

# ==================== 5. 亚克力 & macOS HTML/CSS 模板 ====================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>高中英语自适应学习系统</title>
    <style>
        :root {
            --bg-gradient: linear-gradient(135deg, #100e17, #1e1b29, #0f0c1b);
            --bg-color: #1a1625;
            --text-color: #f1f0f7;
            --sidebar-bg: rgba(15, 15, 27, 0.4);
            --card-bg: rgba(255, 255, 255, 0.03);
            --border-glow: 1px solid rgba(255, 255, 255, 0.08);
            --accent-color: #a78bfa;
            --success-color: #34d399;
            --error-color: #f87171;
            --border-radius: 16px;
            --font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Helvetica, sans-serif;
        }
        
        /* 极致柔雾粉日间主题 */
        body.light-theme {
            --bg-gradient: linear-gradient(135deg, #fdf9fa, #fbf2f0, #fefbfc);
            --bg-color: #fdf9fa;
            --text-color: #4f3a3c;
            --sidebar-bg: rgba(251, 241, 242, 0.75);
            --card-bg: rgba(255, 255, 255, 0.7);
            --border-glow: 1px solid rgba(215, 175, 180, 0.2);
            --accent-color: #d89fa8; 
            --success-color: #8cbfa0; 
            --error-color: #e5938f; 
        }
        body {
            background: var(--bg-gradient);
            color: var(--text-color);
            font-family: var(--font-family);
            margin: 0;
            display: flex;
            height: 100vh;
            transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
            letter-spacing: -0.022em;
        }
        #sidebar {
            width: 250px;
            background-color: var(--sidebar-bg);
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            padding: 30px 20px;
            display: flex;
            flex-direction: column;
            border-right: var(--border-glow);
            box-shadow: 10px 0 30px rgba(0,0,0,0.15);
        }
        #main-content {
            flex: 1;
            padding: 40px;
            overflow-y: auto;
            backdrop-filter: blur(5px);
        }
        h2, h1 {
            font-weight: 700;
            letter-spacing: -0.025em;
            margin-top: 0;
        }
        .nav-btn {
            background: transparent;
            border: none;
            color: var(--text-color);
            padding: 14px 18px;
            text-align: left;
            font-size: 15px;
            font-weight: 500;
            cursor: pointer;
            border-radius: var(--border-radius);
            margin-bottom: 8px;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            display: flex;
            align-items: center;
        }
        .nav-btn:hover {
            background: rgba(255, 255, 255, 0.08);
            transform: translateX(2px);
        }
        .nav-btn.active {
            background: var(--accent-color);
            color: #fff;
            box-shadow: 0 8px 24px rgba(167, 139, 250, 0.3);
        }
        .card {
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: var(--border-glow);
            padding: 30px;
            border-radius: var(--border-radius);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
            margin-bottom: 25px;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
        }
        .option-btn {
            display: block;
            width: 100%;
            background: rgba(255,255,255,0.03);
            border: var(--border-glow);
            color: var(--text-color);
            padding: 18px;
            text-align: left;
            margin-bottom: 12px;
            border-radius: var(--border-radius);
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .option-btn:hover {
            background: rgba(255, 255, 255, 0.08);
            border-color: var(--accent-color);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.25);
        }
        
        .cloze-full-input {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: var(--border-radius);
            color: var(--text-color);
            padding: 14px 20px;
            font-size: 20px;
            width: 100%;
            max-width: 350px;
            text-align: center;
            outline: none;
            transition: all 0.3s;
            margin-bottom: 25px;
            font-weight: 600;
            letter-spacing: 0.05em;
        }
        body.light-theme .cloze-full-input {
            background: rgba(255, 255, 255, 0.8);
            border: 1px solid rgba(215, 175, 180, 0.3);
        }
        .cloze-full-input:focus {
            border-color: var(--accent-color);
            box-shadow: 0 0 12px rgba(167, 139, 250, 0.2);
            background: rgba(255, 255, 255, 0.08);
        }

        .sentence-container {
            font-size: 22px;
            line-height: 2.2;
            margin-bottom: 30px;
            font-weight: 500;
            text-align: center; 
        }

        .btn-submit {
            background: var(--accent-color);
            color: #fff;
            padding: 12px 30px;
            border: none;
            border-radius: var(--border-radius);
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .btn-submit:hover {
            opacity: 0.95;
            transform: translateY(-1px);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 14px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            text-align: left;
        }
        
        .segmented-control {
            display: flex;
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: var(--border-glow);
            border-radius: var(--border-radius);
            padding: 4px;
            gap: 4px;
            max-width: 500px;
            margin-bottom: 20px;
        }
        .segment-btn {
            flex: 1;
            background: transparent;
            border: none;
            color: var(--text-color);
            padding: 10px 15px;
            border-radius: 12px;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            font-family: var(--font-family);
        }
        .segment-btn:hover {
            background: rgba(255, 255, 255, 0.05);
        }
        .segment-btn.active {
            background: var(--accent-color);
            color: #fff;
            box-shadow: 0 4px 12px rgba(167, 139, 250, 0.25);
        }

        .checkbox-container {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 20px;
            background: rgba(255, 255, 255, 0.01);
            border: var(--border-glow);
            border-radius: var(--border-radius);
            margin-bottom: 10px;
            cursor: pointer;
            user-select: none;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .checkbox-container:hover {
            background: rgba(255, 255, 255, 0.05);
            border-color: var(--accent-color);
        }
        .checkbox-container input[type="checkbox"] {
            display: none; 
        }
        .toggle-switch {
            width: 44px;
            height: 24px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            position: relative;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        .toggle-switch::after {
            content: '';
            position: absolute;
            width: 18px;
            height: 18px;
            background: #ffffff;
            border-radius: 50%;
            top: 2px;
            left: 2px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .checkbox-container input[type="checkbox"]:checked + .toggle-switch {
            background: var(--accent-color);
            border-color: var(--accent-color);
            box-shadow: 0 0 8px rgba(167, 139, 250, 0.4);
        }
        .checkbox-container input[type="checkbox"]:checked + .toggle-switch::after {
            transform: translateX(20px);
        }

        #quiz-panel {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center; 
        }
        #quiz-question-title {
            width: 100%;
            text-align: center;
        }
        #quiz-interaction {
            width: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
    </style>
</head>
<body class="lang-cn">
    <div id="sidebar">
        <h2>Vocab v6.0</h2>
        <button class="nav-btn active" onclick="switchTab('dashboard')">⏱️ 仪表盘</button>
        <button class="nav-btn" onclick="switchTab('study')">📖 测试练习</button>
        <button class="nav-btn" onclick="switchTab('pools')">🔄 子词词表</button>
        <button class="nav-btn" onclick="switchTab('logs')">📈 历史日志</button>

        <div class="theme-selector">
            <span style="font-size:13px; opacity:0.7; margin-bottom:8px; display:block;">视觉主题</span>
            <div class="segmented-control" style="max-width: 100%; margin-bottom: 0;">
                <button id="theme-btn-dark" class="segment-btn active" onclick="setTheme('dark')">夜间模式</button>
                <button id="theme-btn-light" class="segment-btn" onclick="setTheme('light')">柔雾粉</button>
            </div>
        </div>

        <!-- 左下角终止进程关机键 -->
        <div style="margin-top: auto; padding-top: 20px;">
            <button class="nav-btn" style="color: var(--error-color); width: 100%; justify-content: flex-start; background: rgba(248, 113, 113, 0.05); border: 1px solid rgba(248, 113, 113, 0.15);" onclick="shutdownBackend()">
                <span style="margin-right: 10px; font-size: 16px;">⏻</span> 终止系统进程
            </button>
        </div>
    </div>

    <div id="main-content">
        <!-- 仪表盘选项卡 -->
        <div id="tab-dashboard" class="tab-content">
            <h1>总览</h1>
            <div class="grid">
                <div class="card">
                    <h3 style="margin-top:0;opacity:0.7;">当前激活范围</h3>
                    <p id="active-pool-name" style="font-size: 20px; font-weight:700;">-</p>
                </div>
                <div class="card">
                    <h3 style="margin-top:0;opacity:0.7;">词库基数</h3>
                    <p id="active-pool-count" style="font-size: 28px; font-weight:700;">0</p>
                </div>
                <div class="card">
                    <h3 style="margin-top:0;opacity:0.7;">到期需复习</h3>
                    <p id="due-count" style="font-size: 28px; font-weight:700; color:var(--accent-color)">0</p>
                </div>
            </div>
            
            <div class="card">
                <h2>🔥 高频错误单词 (Top 15)</h2>
                <div id="stats-table">加载中...</div>
            </div>
        </div>

        <!-- 练习选项卡 -->
        <div id="tab-study" class="tab-content" style="display:none;">
            <h1>测试练习</h1>
            
            <div id="setup-panel" class="card">
                <h3>参数配置</h3>
                <label>测试题型：</label>
                <div class="segmented-control" style="max-width: 100%;">
                    <button id="mode-btn-1" class="segment-btn active" onclick="setMode('1')">看词辨义</button>
                    <button id="mode-btn-2" class="segment-btn" onclick="setMode('2')">完形拼写</button>
                    <button id="mode-btn-3" class="segment-btn" onclick="setMode('3')">词形变化</button>
                    <button id="mode-btn-4" class="segment-btn" onclick="setMode('4')">混合挑战</button>
                </div>

                <label>本次测试题量：</label>
                <input type="number" id="ques-count" value="5" min="1" max="100" style="margin-bottom:20px; display:block; width:100%; max-width:300px; padding:12px; background:rgba(0,0,0,0.15); color:var(--text-color); border:var(--border-glow); border-radius:var(--border-radius); box-sizing:border-box;"><br>
                
                <label class="checkbox-container" style="max-width:300px; margin-bottom:10px;">
                    <span>答对后自动下一题</span>
                    <input type="checkbox" id="auto-advance-select" checked onchange="toggleAutoAdvanceUI()">
                    <div class="toggle-switch"></div>
                </label>
                
                <div id="delay-input-container" style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.01); border:var(--border-glow); padding:10px 15px; border-radius:var(--border-radius); max-width:300px; margin-bottom:20px; box-sizing:border-box; transition:all 0.3s;">
                    <span style="font-size:14px; opacity:0.8;">等待时间 (秒)：</span>
                    <input type="number" id="auto-advance-delay" value="3" min="1" max="10" style="width:60px; padding:6px; border-radius:8px; border:var(--border-glow); background:rgba(0,0,0,0.15); color:var(--text-color); text-align:center; outline:none;">
                </div>

                <label class="checkbox-container" style="max-width:300px; margin-bottom:10px;">
                    <span>无操作自动显示释义</span>
                    <input type="checkbox" id="auto-hint-select" checked onchange="toggleAutoHintUI()">
                    <div class="toggle-switch"></div>
                </label>
                
                <div id="hint-delay-container" style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.01); border:var(--border-glow); padding:10px 15px; border-radius:var(--border-radius); max-width:300px; margin-bottom:20px; box-sizing:border-box; transition:all 0.3s;">
                    <span style="font-size:14px; opacity:0.8;">提示等待时间 (秒)：</span>
                    <input type="number" id="auto-hint-delay" value="8" min="1" max="30" style="width:60px; padding:6px; border-radius:8px; border:var(--border-glow); background:rgba(0,0,0,0.15); color:var(--text-color); text-align:center; outline:none;">
                </div>
                
                <button class="btn-submit" onclick="startQuiz()">开启测试</button>
            </div>

            <div id="quiz-panel" class="card" style="display:none;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:25px; width: 100%;">
                    <span id="quiz-progress" style="font-weight:700; color:var(--accent-color);">Progress: 0/0</span>
                    <button class="btn-submit" style="background:var(--error-color); padding:8px 18px;" onclick="exitQuiz()">中止退出</button>
                </div>
                <h2 id="quiz-question-title" style="font-size:24px; line-height:1.4; margin-bottom:25px;">-</h2>
                <div id="quiz-interaction"></div>
                <div id="quiz-feedback" style="margin-top:20px; line-height:1.6; text-align:center;"></div>
                <button id="next-btn" class="btn-submit" style="display:none; margin-top:20px; width:100%;" onclick="fetchQuestion()">下一题</button>
            </div>
        </div>

        <!-- 词表选项卡 -->
        <div id="tab-pools" class="tab-content" style="display:none;">
            <h1>子词词表管理</h1>
            
            <div class="card">
                <h3>📥 导入外部本地词库</h3>
                <p style="opacity:0.7;">支持无损导入符合规范的 JSON 文件或 TXT 本地路径。</p>
                <input type="text" id="import-path" placeholder="输入文件路径 (例如: E:\\little-corn\\unit4.json)" style="width:100%; padding:15px; margin-bottom:15px; border-radius:var(--border-radius); border:var(--border-glow); background:rgba(0,0,0,0.15); color:var(--text-color); box-sizing:border-box;">
                <button class="btn-submit" onclick="importFile()">执行导入</button>
            </div>

            <div class="card">
                <div style="display:flex; gap:10px; margin-bottom:20px; flex-wrap: wrap;">
                    <button class="btn-submit" onclick="savePoolSelections()">保存词表勾选</button>
                    <button class="btn-submit" style="background:rgba(255,255,255,0.08); border:var(--border-glow);" onclick="selectAllPools(true)">一键全选</button>
                    <button class="btn-submit" style="background:rgba(255,255,255,0.08); border:var(--border-glow);" onclick="selectAllPools(false)">一键全不选</button>
                </div>
                
                <div style="display:flex; gap:10px; align-items:center; margin-top:15px; background:rgba(255,255,255,0.02); padding:12px; border-radius:var(--border-radius); border:var(--border-glow); width:100%; max-width:450px; box-sizing:border-box;">
                    <span style="font-size:14px; opacity:0.8;">区间取反 (例如 [1,3] 或 1-3)：</span>
                    <input type="text" id="range-toggle-input" placeholder="[1,3]" style="width:80px; padding:8px; border-radius:8px; border:var(--border-glow); background:rgba(0,0,0,0.15); color:var(--text-color); text-align:center; outline:none;">
                    <button class="btn-submit" style="padding:6px 15px; font-size:13px;" onclick="applyRangeToggle()">执行取反</button>
                </div>
                
                <div id="pools-list" style="margin-top:20px;">加载中...</div>
            </div>
        </div>

        <!-- 日志选项卡 -->
        <div id="tab-logs" class="tab-content" style="display:none;">
            <h1>历史背词日志与管理</h1>
            <div id="logs-summary" class="card" style="font-size:16px; line-height:1.6;">-</div>
            
            <div class="card" style="display:flex; gap:15px; margin-bottom:25px;">
                <button class="btn-submit" onclick="exportWeakWords()">📉 导出个人弱项复盘清单 (Markdown)</button>
                <button class="btn-submit" style="background:var(--error-color)" onclick="resetAllData()">🚨 物理重置系统数据</button>
            </div>

            <div class="card">
                <div id="logs-table">加载中...</div>
            </div>
        </div>
    </div>

    <script>
        let selectedQuizMode = '1';
        let currentQuestionData = {}; 
        let nextBtnTimer = null; 
        let autoAdvanceEnabled = true; 
        let autoAdvanceDelay = 3000;   
        let hintTimer = null;          
        let autoHintEnabled = true;    
        let autoHintDelay = 8000;      

        function setTheme(theme) {
            document.querySelectorAll('.theme-selector .segment-btn').forEach(btn => btn.classList.remove('active'));
            if(theme === 'light') {
                document.body.classList.add('light-theme');
                document.getElementById('theme-btn-light').classList.add('active');
            } else {
                document.body.classList.remove('light-theme');
                document.getElementById('theme-btn-dark').classList.add('active');
            }
        }
        function setMode(mode) {
            selectedQuizMode = mode;
            document.querySelectorAll('.segmented-control .segment-btn').forEach(btn => btn.classList.remove('active'));
            let btn = document.getElementById('mode-btn-' + mode);
            if(btn) btn.classList.add('active');
        }
        function switchTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
            document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
            document.getElementById('tab-' + tabId).style.display = 'block';
            
            document.querySelectorAll(`.nav-btn[onclick="switchTab('${tabId}')"]`).forEach(el => el.classList.add('active'));
            
            if (tabId === 'dashboard') loadDashboard();
            if (tabId === 'pools') loadPools();
            if (tabId === 'logs') loadLogs();
        }

        function toggleAutoAdvanceUI() {
            let enabled = document.getElementById('auto-advance-select').checked;
            let container = document.getElementById('delay-input-container');
            let delayInput = document.getElementById('auto-advance-delay');
            if(enabled) {
                container.style.opacity = '1';
                delayInput.disabled = false;
            } else {
                container.style.opacity = '0.4';
                delayInput.disabled = true;
            }
        }

        function toggleAutoHintUI() {
            let enabled = document.getElementById('auto-hint-select').checked;
            let container = document.getElementById('hint-delay-container');
            let delayInput = document.getElementById('auto-hint-delay');
            if(enabled) {
                container.style.opacity = '1';
                delayInput.disabled = false;
            } else {
                container.style.opacity = '0.4';
                delayInput.disabled = true;
            }
        }

        async function loadDashboard() {
            let res = await fetch('/api/get_status');
            let data = await res.json();
            document.getElementById('active-pool-name').innerText = data.pool_name;
            document.getElementById('active-pool-count').innerText = data.pool_count;
            document.getElementById('due-count').innerText = data.due_count;

            let statsRes = await fetch('/api/get_stats');
            let stats = await statsRes.json();
            let html = '<table><tr><th>单词</th><th>意思错误</th><th>拼写错误</th><th>总错次</th></tr>';
            stats.forEach(item => {
                html += `<tr><td><b>${item[0]}</b></td><td>${item[1].meaning_errors || 0}</td><td>${item[1].spelling_errors || 0}</td><td>${(item[1].meaning_errors || 0)+(item[1].spelling_errors || 0)}</td></tr>`;
            });
            html += '</table>';
            document.getElementById('stats-table').innerHTML = html;
        }

        async function loadPools() {
            let res = await fetch('/api/get_pools');
            let data = await res.json();
            let html = '';
            data.forEach((item, idx) => {
                let checked = item.selected ? 'checked' : '';
                html += `
                <label class="checkbox-container">
                    <span><strong>[${idx + 1}]</strong> ${item.key} (${item.count} 词)</span>
                    <input type="checkbox" name="pool-key" value="${item.key}" ${checked}>
                    <div class="toggle-switch"></div>
                </label>`;
            });
            document.getElementById('pools-list').innerHTML = html;
        }

        function selectAllPools(status) {
            document.querySelectorAll('input[name="pool-key"]').forEach(cb => {
                cb.checked = status;
            });
        }

        function applyRangeToggle() {
            let val = document.getElementById('range-toggle-input').value.trim();
            if (!val) return;
            
            let matches = val.match(/\\[?\\s*(\\d+)\\s*,\\s*(\\d+)\\s*\\]?/);
            if (!matches) {
                matches = val.match(/(\\d+)\\s*-\\s*(\\d+)/);
            }
            if (matches) {
                let l = parseInt(matches[1]);
                let r = parseInt(matches[2]);
                if (l > r) { let tmp = l; l = r; r = tmp; } 
                
                let checkboxes = document.querySelectorAll('input[name="pool-key"]');
                for (let idx = l; idx <= r; idx++) {
                    if (idx >= 1 && idx <= checkboxes.length) {
                        checkboxes[idx - 1].checked = !checkboxes[idx - 1].checked;
                    }
                }
                document.getElementById('range-toggle-input').value = '';
            } else {
                alert('请输入合法的区间格式，如 [1,3] 或 1-3');
            }
        }

        async function savePoolSelections() {
            let checkboxes = document.querySelectorAll('input[name="pool-key"]:checked');
            let keys = Array.from(checkboxes).map(cb => cb.value);
            await fetch('/api/select_pools', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({keys: keys})
            });
            alert('保存成功！');
            loadDashboard();
        }

        async function loadLogs() {
            let res = await fetch('/api/get_logs');
            let data = await res.json();
            
            let sum_html = `<strong>历史累计统计：</strong> 练习次数: ${data.total_sessions} 次 | 刷题总量: ${data.total_questions} 道 | 做错总数: ${data.total_errors} 道 | 实际错误率: <span style="color:var(--error-color); font-weight:700;">${data.error_rate}%</span> | 累计用时: ${data.total_time}`;
            document.getElementById('logs-summary').innerHTML = sum_html;

            let html = '<table><tr><th>时间</th><th>题型</th><th>做题量</th><th>答错数</th><th>实际正确率</th><th>耗时</th></tr>';
            data.logs.forEach(l => {
                let accuracy = l.total > 0 ? (((l.total - l.errors)/l.total)*100).toFixed(1) + '%' : '0%';
                html += `<tr><td>${l.time}</td><td>${l.mode}</td><td>${l.total}</td><td>${l.errors}</td><td>${accuracy}</td><td>${l.duration}</td></tr>`;
            });
            html += '</table>';
            document.getElementById('logs-table').innerHTML = html;
        }

        async function importFile() {
            let path = document.getElementById('import-path').value;
            let res = await fetch('/api/import_file', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({path: path})
            });
            let data = await res.json();
            if(data.success) {
                alert(`导入成功！共导入新词条 ${data.count} 个`);
                document.getElementById('import-path').value = '';
                loadDashboard();
            } else {
                alert('错误: ' + data.error);
            }
        }

        async function exportWeakWords() {
            let res = await fetch('/api/export_weak', {method: 'POST'});
            let data = await res.json();
            if(data.success) {
                alert(`导出成功！报告已保存在同级目录下: ${data.path}`);
            } else {
                alert('导出失败: ' + data.error);
            }
        }

        async function resetAllData() {
            if(confirm('警告！此操作不可逆，将彻底清空本地所有背词统计、生词本以及自选配置，恢复至系统初始状态！是否确定？')) {
                if(confirm('再次确认：是否执行重置？')) {
                    let res = await fetch('/api/reset_all', {method: 'POST'});
                    let data = await res.json();
                    if(data.success) {
                        alert('系统数据已全部重置，程序将自动关闭。请手动重启以拉起纯净系统。');
                        window.close();
                    }
                }
            }
        }

        // 🌟 核心改进：发送完退出指令后，网页能正常转入“已关机页面”而不会报错弹窗
        async function shutdownBackend() {
            if(confirm('确定要安全终止系统后端进程吗？\\n终止后当前背词网页将断开服务并锁定。')) {
                try {
                    // 先在本地完成关机界面的 UI 切换，避免网络连接断开后 fetch 失败引发 catch 异常
                    let shutdownPageHtml = `
                        <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100vh; font-family:var(--font-family); background:var(--bg-gradient); color:var(--text-color);">
                            <h1 style="color:var(--error-color); font-size:48px; margin-bottom:10px;">⏻ 后端进程已安全关闭</h1>
                            <p style="opacity:0.8; font-size:18px;">命令行 CMD 窗口已成功退出，您可以安全关闭此浏览器标签页。</p>
                        </div>`;
                    
                    fetch('/api/shutdown', { method: 'POST' }).catch(() => {});
                    document.body.innerHTML = shutdownPageHtml;
                } catch(e) {
                    // 容错处理
                }
            }
        }

        async function startQuiz() {
            let count = document.getElementById('ques-count').value;
            autoAdvanceEnabled = document.getElementById('auto-advance-select').checked;
            let delaySeconds = parseInt(document.getElementById('auto-advance-delay').value) || 3;
            autoAdvanceDelay = delaySeconds * 1000;
            
            autoHintEnabled = document.getElementById('auto-hint-select').checked;
            let hintSeconds = parseInt(document.getElementById('auto-hint-delay').value) || 8;
            autoHintDelay = hintSeconds * 1000;
            
            await fetch('/api/start_quiz', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({mode: selectedQuizMode, count: parseInt(count)})
            });
            document.getElementById('setup-panel').style.display = 'none';
            document.getElementById('quiz-panel').style.display = 'block';
            fetchQuestion();
        }

        async function exitQuiz() {
            if(nextBtnTimer) clearTimeout(nextBtnTimer);
            if(hintTimer) clearTimeout(hintTimer);
            await fetch('/api/exit_quiz');
            document.getElementById('setup-panel').style.display = 'block';
            document.getElementById('quiz-panel').style.display = 'none';
        }

        function showHintAutomatically() {
            let box = document.getElementById('quiz-hint-box');
            if (box) {
                box.style.display = 'block';
            }
        }

        async function fetchQuestion() {
            if(nextBtnTimer) {
                clearTimeout(nextBtnTimer);
                nextBtnTimer = null;
            }
            if(hintTimer) {
                clearTimeout(hintTimer);
                hintTimer = null;
            }
            document.getElementById('quiz-feedback').innerHTML = '';
            document.getElementById('next-btn').style.display = 'none';
            
            let res = await fetch('/api/get_question');
            let data = await res.json();
            currentQuestionData = data; 

            if(data.finished) {
                let acc = data.report.answered > 0 ? (((data.report.answered - data.report.errors)/data.report.answered)*100).toFixed(1) + '%' : '0%';
                let resultHtml = `<h2>测试完毕！</h2>
                <p>实际完成: ${data.report.answered} 道 | 答错: ${data.report.errors} 道</p>
                <p>实际正确率: <span style="color:var(--success-color); font-size:24px;">${acc}</span></p>
                <p>练习用时: ${data.report.duration}</p>
                <button class="btn-submit" onclick="exitQuiz()">返回主页</button>`;
                document.getElementById('quiz-interaction').innerHTML = resultHtml;
                document.getElementById('quiz-question-title').innerText = '测试结算';
                return;
            }

            document.getElementById('quiz-progress').innerText = `Progress: ${data.step}/${data.total}`;

            let html = '';
            if(data.mode === '1') {
                document.getElementById('quiz-question-title').innerText = data.title;
                data.options.forEach((opt, idx) => {
                    html += `<button class="option-btn" onclick="submitAnswer('${idx+1}')">${idx+1}. ${opt}</button>`;
                });
            } else {
                let renderFirstLetterHint = data.first_letter ? data.first_letter + '...' : '______';
                let renderedSentence = `${data.sentence_before}<span style="border-bottom:2px dashed var(--accent-color); color:var(--accent-color); font-weight:700; padding: 0 4px;"> ${renderFirstLetterHint} </span>${data.sentence_after}`;
                
                if(data.mode === '2') {
                    renderedSentence += ` (${data.placeholder_length + 1} 个字母)`;
                }
                
                html += `<div class="sentence-container">${renderedSentence}</div>`;
                
                if(data.prompt_word) {
                    html += `<div style="font-size:18px; margin-bottom:20px; color:var(--accent-color); font-weight:700; width:100%; text-align:center;">提示词: ${data.prompt_word}</div>`;
                }

                let placeholderText = data.first_letter ? `首字母为 ${data.first_letter}，请输入完整单词` : "请输入完整单词";
                html += `<input type="text" id="full-spelling-answer" class="cloze-full-input" placeholder="${placeholderText}" onkeydown="if(event.key==='Enter') submitAnswer(this.value.trim())">`;

                html += `<div style="display:flex; justify-content:center; gap:15px; align-items:center; width:100%;">
                    <button class="btn-submit" onclick="submitAnswer(document.getElementById('full-spelling-answer').value.trim())">提交答案</button>
                    <button class="btn-submit" style="background:rgba(255,255,255,0.08); border:var(--border-glow);" onclick="toggleHint()">💡 显示释义提示</button>
                </div>`;
                
                if(data.chinese_hint) {
                    html += `<div id="quiz-hint-box" style="display:none; margin-top:20px; font-size:16px; color:var(--accent-color); padding:15px; border-radius:var(--border-radius); background:rgba(255,255,255,0.02); border:var(--border-glow); width:100%; max-width:600px; box-sizing:border-box;">
                        <strong>提示：</strong> ${data.chinese_hint}
                    </div>`;
                }
                
                document.getElementById('quiz-question-title').innerText = '根据语境拼写单词';
            }
            document.getElementById('quiz-interaction').innerHTML = html;
            
            let fullInputEl = document.getElementById('full-spelling-answer');
            if(fullInputEl) fullInputEl.focus();

            if(data.mode !== '1' && data.chinese_hint && autoHintEnabled) {
                hintTimer = setTimeout(() => {
                    showHintAutomatically();
                }, autoHintDelay);
            }
        }

        function toggleHint() {
            let box = document.getElementById('quiz-hint-box');
            if(box) {
                box.style.display = box.style.display === 'none' ? 'block' : 'none';
            }
        }

        async function submitAnswer(ans) {
            if(nextBtnTimer) {
                clearTimeout(nextBtnTimer);
                nextBtnTimer = null;
            }
            if(hintTimer) {
                clearTimeout(hintTimer);
                hintTimer = null;
            }
            let res = await fetch('/api/submit_answer', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({answer: ans})
            });
            let data = await res.json();
            
            let feedback = document.getElementById('quiz-feedback');
            if(data.correct) {
                if(autoAdvanceEnabled) {
                    let delaySecs = autoAdvanceDelay / 1000;
                    feedback.innerHTML = `<span style="color:var(--success-color); font-size:18px;">✔ [正确]</span> <small style="opacity:0.6; margin-left:10px;">(${delaySecs}秒后自动切入下一题)</small>`;
                    nextBtnTimer = setTimeout(() => {
                        fetchQuestion();
                    }, autoAdvanceDelay);
                } else {
                    feedback.innerHTML = `<span style="color:var(--success-color); font-size:18px;">✔ [正确]</span>`;
                }
            } else {
                let errHtml = `<span style="color:var(--error-color); font-size:18px;">❌ [错误]</span> 正确答案是: <strong style="color:var(--success-color); font-size:20px;">${data.correct_spelling}</strong><br>释义: ${data.meanings.join('/')}`;
                if(data.options_analysis) {
                    errHtml += `<br><br><small style="color:var(--accent-color); font-weight:700;">选项原词解析：</small><br>`;
                    data.options_analysis.forEach(item => {
                        errHtml += `<small style="display:block; margin-top:5px; opacity:0.8;">• ${item.meaning} -> <strong>${item.word}</strong> (${item.pos})</small>`;
                    });
                }
                feedback.innerHTML = errHtml;
            }
            document.getElementById('next-btn').style.display = 'block';
            document.getElementById('next-btn').focus();
        }

        document.addEventListener('click', function(event) {
            let nextBtn = document.getElementById('next-btn');
            if(nextBtn && nextBtn.style.display === 'block') {
                if(event.target !== nextBtn && event.target.tagName !== 'BUTTON' && event.target.tagName !== 'INPUT') {
                    fetchQuestion();
                }
            }
        });

        document.addEventListener('keydown', function(event) {
            if(event.key === 'Enter') {
                let nextBtn = document.getElementById('next-btn');
                if(nextBtn && nextBtn.style.display === 'block') {
                    fetchQuestion();
                    event.preventDefault(); 
                }
            }
        });

        loadDashboard();
    </script>
</body>
</html>
"""

# ==================== 6. 路由及后端 API 控制 ====================
def api_response(start_response, data):
    status = '200 OK'
    headers = [
        ('Content-type', 'application/json; charset=utf-8'),
        ('Access-Control-Allow-Origin', '*')
    ]
    start_response(status, headers)
    return [json.dumps(data, ensure_ascii=False).encode('utf-8')]

def wsgi_app(environ, start_response):
    path = environ.get('PATH_INFO', '')
    method = environ.get('REQUEST_METHOD', 'GET')
    
    if path == '/' or path == '/index.html':
        start_response('200 OK', [('Content-type', 'text/html; charset=utf-8')])
        return [HTML_TEMPLATE.encode('utf-8')]
        
    # 🌟 终止关机接口（通过微线程延时 0.2 秒退出，保障浏览器可以安全取得回应）
    if path == '/api/shutdown' and method == 'POST':
        print("\n[系统通知] 网页端关机信号已接收，安全释放程序...")
        def kill_proc():
            time.sleep(0.2)
            os._exit(0)
        Thread(target=kill_proc).start()
        return api_response(start_response, {"status": "shutdown_scheduled"})

    if path == '/api/get_status':
        full_bank = {**DEFAULT_WORD_BANK, **dm.custom_bank}
        current_keys = dm.last_selected_keys if dm.last_selected_keys else list(full_bank.keys())
        active_pool = []
        for k in current_keys:
            if k in full_bank: active_pool.extend(full_bank[k])
            
        now_time_iso = datetime.now().isoformat()
        due_count = sum(1 for w in active_pool if dm.stats.get(w['word'], {}).get('next_date', now_time_iso) <= now_time_iso)
        
        return api_response(start_response, {
            "pool_name": "+".join(current_keys) if len(current_keys) <= 2 else f"{current_keys[0]}等{len(current_keys)}个词表",
            "pool_count": len(active_pool),
            "due_count": due_count
        })

    elif path == '/api/get_stats':
        sorted_stats = sorted(dm.stats.items(), key=lambda x: (x[1].get("meaning_errors", 0) + x[1].get("spelling_errors", 0)), reverse=True)
        return api_response(start_response, sorted_stats[:15])

    elif path == '/api/get_pools':
        full_bank = {**DEFAULT_WORD_BANK, **dm.custom_bank}
        pools_data = []
        for k in full_bank:
            pools_data.append({
                "key": k,
                "count": len(full_bank[k]),
                "selected": k in dm.last_selected_keys
            })
        return api_response(start_response, pools_data)

    elif path == '/api/select_pools' and method == 'POST':
        try:
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            request_body = environ['wsgi.input'].read(request_body_size)
            data = json.loads(request_body.decode('utf-8'))
            dm.save_config(data.get("keys", []))
            return api_response(start_response, {"success": True})
        except Exception as e:
            return api_response(start_response, {"error": str(e)})

    elif path == '/api/get_logs':
        def get_seconds(log_item):
            if "raw_duration" in log_item:
                return log_item["raw_duration"]
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
        error_rate = f"{((total_errors / total_questions) * 100):.1f}" if total_questions > 0 else "0.0"

        return api_response(start_response, {
            "logs": list(reversed(dm.logs)),
            "total_sessions": total_sessions,
            "total_questions": total_questions,
            "total_errors": total_errors,
            "error_rate": error_rate,
            "total_time": total_time_str
        })

    elif path == '/api/import_file' and method == 'POST':
        try:
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            request_body = environ['wsgi.input'].read(request_body_size)
            body_data = json.loads(request_body.decode('utf-8'))
            file_path = body_data.get("path", "").strip()
            
            if not file_path:
                return api_response(start_response, {"error": "文件路径不能为空"})
            if not os.path.exists(file_path):
                return api_response(start_response, {"error": "路径无效，未找到指定词库文件"})
                
            is_json = False
            with open(file_path, 'r', encoding='utf-8') as f:
                sample = f.read(150).strip()
                if sample.startswith("{") or file_path.lower().endswith(".json"):
                    is_json = True
            
            imported_count = 0
            if is_json:
                with open(file_path, 'r', encoding='utf-8') as f:
                    new_data = json.load(f)
                for sec, words in new_data.items():
                    if sec not in dm.custom_bank:
                        dm.custom_bank[sec] = []
                    for word_item in words:
                        if not any(item['word'] == word_item['word'] for item in dm.custom_bank[sec]):
                            dm.custom_bank[sec].append(word_item)
                            imported_count += 1
            else:
                current_section = "外部导入词表"
                relations_to_wire = []
                with open(file_path, 'r', encoding='utf-8') as f:
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
            return api_response(start_response, {"success": True, "count": imported_count})
        except Exception as e:
            return api_response(start_response, {"error": str(e)})

    elif path == '/api/export_weak' and method == 'POST':
        try:
            filename = "Weak_Words_Report.md"
            with open(filename, "w", encoding='utf-8') as f:
                f.write("# 📓 英语弱项高频错词复盘清单\n\n")
                f.write("| 单词 | 义项错误 | 拼写错误 | 记忆间隔(天) | 下次建议复习日期 |\n")
                for w, s in dm.stats.items():
                    m_err = s.get("meaning_errors", 0)
                    s_err = s.get("spelling_errors", 0)
                    if (m_err + s_err) > 0:
                        f.write(f"| **{w}** | {m_err} | {s_err} | {s.get('interval', 0)} 天 | {s.get('next_date', '')[:10]} |\n")
            return api_response(start_response, {"success": True, "path": filename})
        except Exception as e:
            return api_response(start_response, {"error": str(e)})

    elif path == '/api/reset_all' and method == 'POST':
        try:
            dm.clear_all_data()
            return api_response(start_response, {"success": True})
        except Exception as e:
            return api_response(start_response, {"error": str(e)})

    elif path == '/api/start_quiz' and method == 'POST':
        request_body_size = int(environ.get('CONTENT_LENGTH', 0))
        request_body = environ['wsgi.input'].read(request_body_size)
        data = json.loads(request_body.decode('utf-8'))
        
        full_bank = {**DEFAULT_WORD_BANK, **dm.custom_bank}
        current_keys = dm.last_selected_keys if dm.last_selected_keys else list(full_bank.keys())
        active_pool = []
        for k in current_keys:
            if k in full_bank: active_pool.extend(full_bank[k])
            
        now_time_iso = datetime.now().isoformat()
        due_pool = [w for w in active_pool if dm.stats.get(w['word'], {}).get('next_date', now_time_iso) <= now_time_iso]
        pool_to_draw = due_pool if due_pool else active_pool
        
        ss.current_pool = active_pool
        ss.quiz_words = [random.choice(pool_to_draw) for _ in range(data.get("count", 5))]
        ss.total_ques = data.get("count", 5)
        ss.current_index = 0
        ss.error_count = 0
        ss.answered_count = 0  
        ss.start_time = time.perf_counter()
        ss.current_mode = str(data.get("mode", "1"))
        return api_response(start_response, {"success": True})

    elif path == '/api/exit_quiz':
        if ss.answered_count > 0:
            duration = time.perf_counter() - ss.start_time
            actual_mode_name = "形似字义辨析" if ss.current_mode=='1' else "完形空缺拼写" if ss.current_mode=='2' else "语法填空词形变化" if ss.current_mode=='3' else "综合模式"
            dm.add_study_log(actual_mode_name, ss.answered_count, ss.error_count, duration)
        ss.quiz_words = []
        return api_response(start_response, {"success": True})

    elif path == '/api/get_question':
        if ss.current_index >= len(ss.quiz_words):
            duration = time.perf_counter() - ss.start_time
            actual_mode_name = "形似字义辨析" if ss.current_mode=='1' else "完形空缺拼写" if ss.current_mode=='2' else "语法填空词形变化" if ss.current_mode=='3' else "综合模式"
            dm.add_study_log(actual_mode_name, ss.answered_count, ss.error_count, duration)
            mins, secs = divmod(int(duration), 60)
            time_str = f"{mins}分{secs}秒" if mins > 0 else f"{secs}秒"
            return api_response(start_response, {
                "finished": True,
                "report": {
                    "answered": ss.answered_count,
                    "errors": ss.error_count,
                    "duration": time_str
                }
            })

        ss.current_word = ss.quiz_words[ss.current_index]
        mode = ss.current_mode if ss.current_mode != '4' else random.choice(['1', '2', '3'])
        
        if mode == '3':
            valid_relations = {
                k: v for k, v in ss.current_word.get("related_forms", {}).items() 
                if k.strip().lower() != ss.current_word['word'].strip().lower()
            }
            if not valid_relations:
                mode = '2'

        res_data = {
            "finished": False,
            "step": ss.current_index + 1,
            "total": ss.total_ques,
            "mode": mode
        }

        if mode == '1':  
            correct_display = random.choice(ss.current_word['meanings'])
            options_data = [(correct_display, ss.current_word['word'])]
            wrong_data = generate_smart_distractors_with_sources(ss.current_word, ss.current_pool)
            options_data.extend(wrong_data)
            random.shuffle(options_data)
            
            ss.options_data = options_data
            res_data["title"] = f"{ss.current_word['word']}"
            res_data["options"] = [item[0] for item in options_data]
            
        elif mode == '2':  
            s_list = ss.current_word.get("sentences", ["-"])
            chosen_sentence = s_list[0]
            
            match = re.search(rf'\b{ss.current_word["word"]}(s|es|ed|ing|d)?\b', chosen_sentence, re.IGNORECASE)
            if match:
                matched_word = match.group(0)
                ss.expected_answer = matched_word 
                w_len = len(matched_word)
                start, end = match.start(), match.end()
                res_data["sentence_before"] = chosen_sentence[:start]
                res_data["sentence_after"] = chosen_sentence[end:]
                res_data["placeholder_blank"] = " "
                res_data["first_letter"] = matched_word[0]
                res_data["placeholder_length"] = w_len - 1
            else:
                ss.expected_answer = ss.current_word['word']
                w_len = len(ss.current_word['word'])
                res_data["sentence_before"] = chosen_sentence
                res_data["sentence_after"] = ""
                res_data["placeholder_blank"] = " "
                res_data["first_letter"] = ss.current_word['word'][0]
                res_data["placeholder_length"] = w_len - 1
                
            res_data["chinese_hint"] = "/".join(ss.current_word['meanings'])

        else:  
            valid_relations = {
                k: v for k, v in ss.current_word.get("related_forms", {}).items() 
                if k.strip().lower() != ss.current_word['word'].strip().lower()
            }
            base_word, req_pos = random.choice(list(valid_relations.items()))
            chosen_sentence = random.choice(ss.current_word.get("sentences", ["-"]))
            
            match = re.search(rf'\b{ss.current_word["word"]}(s|es|ed|ing|d)?\b', chosen_sentence, re.IGNORECASE)
            if match:
                matched_word = match.group(0)
                ss.expected_answer = matched_word
                w_len = len(matched_word)
                start, end = match.start(), match.end()
                res_data["sentence_before"] = chosen_sentence[:start]
                res_data["sentence_after"] = chosen_sentence[end:]
                res_data["placeholder_blank"] = " "
                res_data["placeholder_length"] = w_len
                res_data["first_letter"] = "" 
            else:
                ss.expected_answer = ss.current_word['word']
                w_len = len(ss.current_word['word'])
                res_data["sentence_before"] = chosen_sentence
                res_data["sentence_after"] = ""
                res_data["placeholder_blank"] = " "
                res_data["placeholder_length"] = w_len
                res_data["first_letter"] = ""
                
            res_data["chinese_hint"] = "/".join(ss.current_word['meanings'])
            res_data["prompt_word"] = base_word
            res_data["prompt_pos"] = req_pos

        return api_response(start_response, res_data)

    elif path == '/api/submit_answer' and method == 'POST':
        request_body_size = int(environ.get('CONTENT_LENGTH', 0))
        request_body = environ['wsgi.input'].read(request_body_size)
        data = json.loads(request_body.decode('utf-8'))
        ans = data.get("answer", "").strip()
        
        is_correct = False
        if ss.options_data:  
            try:
                idx = int(ans) - 1
                is_correct = (0 <= idx < len(ss.options_data) and ss.options_data[idx][1] == ss.current_word['word'])
            except:
                is_correct = False
        else:
            is_correct = (ans.lower() == ss.expected_answer.lower())

        ss.answered_count += 1  
        dm.log_word_attempt(ss.current_word['word'], "spelling" if not ss.options_data else "meaning", is_correct)
        
        res_payload = {
            "correct": is_correct,
            "correct_spelling": ss.expected_answer if not ss.options_data else ss.current_word['word'],
            "meanings": ss.current_word['meanings']
        }
        
        if not is_correct:
            ss.error_count += 1
            if ss.options_data:
                analysis = []
                for meaning_str, word_str in ss.options_data:
                    src_item = next((w for w in ss.current_pool if w['word'] == word_str), None)
                    analysis.append({
                        "meaning": meaning_str,
                        "word": word_str,
                        "pos": src_item.get('hint', 'n.') if src_item else 'n.'
                    })
                res_payload["options_analysis"] = analysis

        ss.options_data = [] 
        ss.current_index += 1
        return api_response(start_response, res_payload)

    start_response('404 NOT FOUND', [('Content-type', 'text/plain')])
    return [b'File Not Found']

# ==================== 7. 系统启动与注册 ====================
def main():
    port = 5000
    try:
        server = make_server('127.0.0.1', port, wsgi_app)
    except OSError:
        port = 5001
        server = make_server('127.0.0.1', port, wsgi_app)
        
    print(f"==========================================")
    print(f" 高中英语自适应背词系统图形化界面已启动！")
    print(f" 运行地址: http://127.0.0.1:{port}")
    print(f"==========================================")
    
    webbrowser.open_new_tab(f"http://127.0.0.1:{port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n系统已退出。")

if __name__ == "__main__":
    main()
