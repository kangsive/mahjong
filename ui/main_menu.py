# -*- coding: utf-8 -*-
"""
主菜单界面
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from game.game_engine import GameEngine, GameMode
from .game_window import GameWindow
from utils.font_config import font_config

class MainMenu:
    """主菜单类"""
    
    def __init__(self, root: tk.Tk, game_engine: GameEngine):
        self.root = root
        self.game_engine = game_engine
        self.game_window: Optional[GameWindow] = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置用户界面"""
        # 清除现有内容
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="🀄 麻将游戏", 
                               style='Title.TLabel')
        title_label.grid(row=0, column=0, pady=(0, 30))
        
        # 副标题
        subtitle_label = ttk.Label(main_frame, 
                                  text="支持训练模式和竞技模式的智能麻将游戏",
                                  font=font_config.get_normal_font(),
                                  foreground='#7f8c8d')
        subtitle_label.grid(row=1, column=0, pady=(0, 40))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, pady=20)
        
        # 训练模式按钮
        training_btn = ttk.Button(button_frame, 
                                 text="🎓 训练模式", 
                                 style='Custom.TButton',
                                 command=self.start_training_mode,
                                 width=20)
        training_btn.grid(row=0, column=0, padx=10, pady=10)
        
        # 竞技模式按钮
        competitive_btn = ttk.Button(button_frame, 
                                   text="⚔️ 竞技模式", 
                                   style='Custom.TButton',
                                   command=self.start_competitive_mode,
                                   width=20)
        competitive_btn.grid(row=0, column=1, padx=10, pady=10)
        
        # 规则选择框架
        rule_frame = ttk.LabelFrame(main_frame, text="游戏规则", padding="10")
        rule_frame.grid(row=3, column=0, pady=20, sticky=(tk.W, tk.E))
        
        self.rule_var = tk.StringVar(value="sichuan")
        
        sichuan_radio = ttk.Radiobutton(rule_frame, 
                                       text="四川麻将（血战到底）", 
                                       variable=self.rule_var, 
                                       value="sichuan")
        sichuan_radio.grid(row=0, column=0, sticky=tk.W, padx=10)
        
        # 暂时只支持四川麻将
        # national_radio = ttk.Radiobutton(rule_frame, 
        #                                 text="国标麻将", 
        #                                 variable=self.rule_var, 
        #                                 value="national",
        #                                 state="disabled")
        # national_radio.grid(row=0, column=1, sticky=tk.W, padx=10)
        
        # 功能介绍框架
        info_frame = ttk.LabelFrame(main_frame, text="功能介绍", padding="10")
        info_frame.grid(row=4, column=0, pady=20, sticky=(tk.W, tk.E))
        
        info_text = """
🎓 训练模式：
• AI训练师实时指导，提供打牌建议
• 详细的策略分析和教学说明
• 适合新手学习麻将技巧

⚔️ 竞技模式：
• 与高水平AI对手竞技
• 真实的对战体验
• 挑战你的麻将技能
        """
        
        info_label = ttk.Label(info_frame, text=info_text.strip(), 
                              justify=tk.LEFT, font=font_config.get_small_font())
        info_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # 底部按钮
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=5, column=0, pady=30)
        
        # 帮助按钮
        help_btn = ttk.Button(bottom_frame, text="❓ 游戏帮助", 
                             command=self.show_help)
        help_btn.grid(row=0, column=0, padx=10)
        
        # 退出按钮
        exit_btn = ttk.Button(bottom_frame, text="❌ 退出游戏", 
                             command=self.exit_game)
        exit_btn.grid(row=0, column=1, padx=10)
        
    def start_training_mode(self):
        """开始训练模式"""
        try:
            rule_type = self.rule_var.get()
            self.game_engine.setup_game(GameMode.TRAINING, rule_type)
            
            # 先隐藏主菜单，再创建游戏窗口
            self.hide_menu()
            
            # 创建游戏窗口
            self.game_window = GameWindow(self.root, self.game_engine, 
                                        is_training_mode=True)
            
        except Exception as e:
            messagebox.showerror("错误", f"启动训练模式失败: {e}")
    
    def start_competitive_mode(self):
        """开始竞技模式"""
        try:
            rule_type = self.rule_var.get()
            self.game_engine.setup_game(GameMode.COMPETITIVE, rule_type)
            
            # 先隐藏主菜单，再创建游戏窗口
            self.hide_menu()
            
            # 创建游戏窗口
            self.game_window = GameWindow(self.root, self.game_engine, 
                                        is_training_mode=False)
            
        except Exception as e:
            messagebox.showerror("错误", f"启动竞技模式失败: {e}")
    
    def show_help(self):
        """显示游戏帮助"""
        help_text = """
🀄 麻将游戏帮助

基本规则：
• 四川麻将使用万、筒、条、风、箭牌
• 每位玩家起手13张牌，庄家14张
• 需要先选择缺一门（万、筒、条中的一种）
• 胡牌条件：4个面子 + 1个对子

面子类型：
• 刻子：三张相同的牌
• 顺子：同花色连续的三张牌
• 对子：两张相同的牌

特殊牌型：
• 碰碰胡：全部刻子，分数 x2
• 清一色：同一花色，分数 x4
• 字一色：全部字牌，分数 x4
• 大三元：中、发、白三个刻子，分数 x8
• 大四喜：东、南、西、北四个刻子，分数 x8

操作说明：
• 点击手牌选择要打出的牌
• 其他玩家打牌后可选择碰、杠、吃、胡牌
• 训练模式会提供实时建议和指导
        """
        
        help_window = tk.Toplevel(self.root)
        help_window.title("游戏帮助")
        help_window.geometry("500x600")
        help_window.resizable(False, False)
        
        # 居中显示
        help_window.transient(self.root)
        help_window.grab_set()
        
        # 创建滚动文本框
        text_frame = ttk.Frame(help_window, padding="10")
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=font_config.get_small_font())
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text_widget.insert('1.0', help_text)
        text_widget.configure(state='disabled')
        
        # 关闭按钮
        close_btn = ttk.Button(help_window, text="关闭", 
                              command=help_window.destroy)
        close_btn.pack(pady=10)
    
    def exit_game(self):
        """退出游戏"""
        if messagebox.askokcancel("退出", "确定要退出游戏吗？"):
            self.root.quit()
    
    def hide_menu(self):
        """隐藏菜单"""
        for widget in self.root.winfo_children():
            widget.pack_forget()
            widget.grid_forget()
    
    def show_menu(self):
        """显示菜单"""
        self.setup_ui()
    
    def on_game_ended(self):
        """游戏结束回调"""
        self.game_window = None
        self.show_menu() 