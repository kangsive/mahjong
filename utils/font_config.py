# -*- coding: utf-8 -*-
"""
字体配置工具
解决中文显示问题
"""

import tkinter as tk
import platform
import subprocess
from typing import List, Optional

class FontConfig:
    """字体配置类"""
    
    def __init__(self):
        self.available_fonts = self._get_available_fonts()
        self.default_font = self._get_best_chinese_font()
        
    def _get_available_fonts(self) -> List[str]:
        """获取系统可用字体"""
        try:
            # 创建一个临时的tkinter窗口来获取字体列表
            root = tk.Tk()
            root.withdraw()  # 隐藏窗口
            
            # 获取tkinter支持的字体
            fonts = list(tk.font.families())
            root.destroy()
            
            return fonts
        except Exception:
            return []
    
    def _get_best_chinese_font(self) -> str:
        """获取最佳中文字体"""
        # 优先级列表，从高到低
        preferred_fonts = [
            "Noto Sans CJK SC",
            "Noto Serif CJK SC", 
            "WenQuanYi Zen Hei",
            "WenQuanYi Micro Hei",
            "SimHei",
            "Microsoft YaHei",
            "Arial Unicode MS",
            "DejaVu Sans",
            "Liberation Sans",
            "FreeSans"
        ]
        
        # 检查每个字体是否可用
        for font in preferred_fonts:
            if self._is_font_available(font):
                return font
        
        # 如果都不可用，使用系统默认字体
        return "TkDefaultFont"
    
    def _is_font_available(self, font_name: str) -> bool:
        """检查字体是否可用"""
        try:
            # 方法1：检查tkinter字体列表
            if font_name in self.available_fonts:
                return True
            
            # 方法2：使用fc-list命令检查（Linux）
            if platform.system() == "Linux":
                result = subprocess.run(
                    ["fc-list", ":", "family"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return font_name in result.stdout
            
            return False
        except Exception:
            return False
    
    def get_font_config(self, size: int = 12, weight: str = "normal") -> tuple:
        """获取字体配置"""
        return (self.default_font, size, weight)
    
    def get_title_font(self) -> tuple:
        """获取标题字体"""
        return self.get_font_config(16, "bold")
    
    def get_normal_font(self) -> tuple:
        """获取普通字体"""
        return self.get_font_config(12, "normal")
    
    def get_small_font(self) -> tuple:
        """获取小字体"""
        return self.get_font_config(10, "normal")

# 全局字体配置实例
font_config = FontConfig() 