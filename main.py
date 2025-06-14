#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麻将游戏主程序
支持训练模式和竞技模式
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

# 添加项目路径到sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.main_menu import MainMenu
from game.game_engine import GameEngine
from utils.logger import setup_logger

class MahjongApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("麻将游戏 - 训练与竞技")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        # 设置窗口图标和样式
        self.setup_window_style()
        
        # 初始化日志
        self.logger = setup_logger()
        
        # 初始化游戏引擎
        self.game_engine = GameEngine()
        
        # 创建主菜单
        self.main_menu = MainMenu(self.root, self.game_engine)
        
        self.logger.info("麻将游戏初始化完成")
    
    def setup_window_style(self):
        """设置窗口样式"""
        self.root.configure(bg='#2c3e50')
        
        # 设置ttk样式
        style = ttk.Style()
        style.theme_use('clam')
        
        # 自定义样式
        style.configure('Title.TLabel', 
                       font=('Microsoft YaHei', 16, 'bold'),
                       background='#2c3e50',
                       foreground='#ecf0f1')
        
        style.configure('Custom.TButton',
                       font=('Microsoft YaHei', 12),
                       padding=10)
    
    def run(self):
        """运行应用程序"""
        try:
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"应用程序运行错误: {e}")
            messagebox.showerror("错误", f"程序运行出现错误: {e}")

def main():
    """主函数"""
    try:
        app = MahjongApp()
        app.run()
    except Exception as e:
        print(f"程序启动失败: {e}")
        messagebox.showerror("启动错误", f"程序启动失败: {e}")

if __name__ == "__main__":
    main() 