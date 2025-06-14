# -*- coding: utf-8 -*-
"""
游戏窗口界面
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, Dict
import threading
import time

from game.game_engine import GameEngine, GameState
from game.tile import Tile, TileType
from game.player import Player, PlayerType

class GameWindow:
    """游戏窗口类"""
    
    def __init__(self, root: tk.Tk, game_engine: GameEngine, is_training_mode: bool = False):
        self.root = root
        self.game_engine = game_engine
        self.is_training_mode = is_training_mode
        
        # UI组件
        self.selected_tile: Optional[Tile] = None
        self.tile_buttons: List[tk.Button] = []
        self.action_buttons: Dict[str, tk.Button] = {}
        
        # 换三张相关
        self.exchange_window = None
        self.selected_exchange_tiles: List[Tile] = []
        
        # 缺一门选择相关
        self.missing_suit_window = None
        
        self.setup_ui()
        self.setup_game_events()
        self.start_game_monitor()
        
    def setup_ui(self):
        """设置用户界面"""
        # 清除现有内容
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 游戏信息
        info_frame = ttk.LabelFrame(main_frame, text="游戏信息", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.game_info_var = tk.StringVar()
        ttk.Label(info_frame, textvariable=self.game_info_var).pack()
        
        # 手牌区域
        self.hand_frame = ttk.LabelFrame(main_frame, text="手牌", padding="10")
        self.hand_frame.pack(fill=tk.X, pady=10)
        
        # 操作按钮
        action_frame = ttk.LabelFrame(main_frame, text="操作", padding="10")
        action_frame.pack(fill=tk.X, pady=10)
        
        actions = [("胡牌", "win"), ("杠", "gang"), ("碰", "peng"), ("过", "pass")]
        for text, action in actions:
            btn = ttk.Button(action_frame, text=text, width=8,
                           command=lambda a=action: self.execute_action(a))
            btn.pack(side=tk.LEFT, padx=5)
            self.action_buttons[action] = btn
        
        # 控制按钮
        control_frame = ttk.Frame(action_frame)
        control_frame.pack(side=tk.RIGHT)
        ttk.Button(control_frame, text="开始游戏", command=self.start_game).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="返回主菜单", command=self.return_to_menu).pack(side=tk.LEFT, padx=5)
        
        # 训练模式建议
        if self.is_training_mode:
            advice_frame = ttk.LabelFrame(main_frame, text="AI建议", padding="10")
            advice_frame.pack(fill=tk.BOTH, expand=True, pady=10)
            self.advice_text = tk.Text(advice_frame, height=6, wrap=tk.WORD)
            self.advice_text.pack(fill=tk.BOTH, expand=True)
        
        # 消息显示区域
        message_frame = ttk.LabelFrame(main_frame, text="消息", padding="10")
        message_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.message_text = tk.Text(message_frame, height=6, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(message_frame, orient=tk.VERTICAL, command=self.message_text.yview)
        self.message_text.configure(yscrollcommand=scrollbar.set)
        
        self.message_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_game_events(self):
        """设置游戏事件回调"""
        # 为人类玩家设置事件回调
        human_player = self.get_human_player()
        if human_player:
            # 换三张事件
            human_player.on_tile_exchange_start = self.on_tile_exchange_start
            # 选择缺一门事件
            human_player.on_missing_suit_selection_start = self.on_missing_suit_selection_start
    
    def start_game_monitor(self):
        """启动游戏状态监控线程"""
        def monitor():
            while True:
                try:
                    self.update_game_display()
                    time.sleep(0.1)  # 100ms更新一次
                except Exception as e:
                    print(f"游戏监控线程错误: {e}")
                    break
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def start_game(self):
        """开始游戏"""
        try:
            success = self.game_engine.start_game()
            if success:
                self.add_message("游戏开始！")
            else:
                messagebox.showerror("错误", "游戏启动失败！")
        except Exception as e:
            messagebox.showerror("错误", f"游戏启动失败: {e}")
    
    def get_human_player(self) -> Optional[Player]:
        """获取人类玩家"""
        for player in self.game_engine.players:
            if player.player_type == PlayerType.HUMAN:
                return player
        return None
    
    def update_game_display(self):
        """更新游戏显示"""
        try:
            # 更新游戏信息
            game_state = self.game_engine.get_game_state()
            state_text = {
                'waiting': '等待开始',
                'dealing': '发牌中',
                'tile_exchange': '换三张阶段',
                'missing_suit_selection': '选择缺一门',
                'playing': '游戏进行中',
                'waiting_action': '等待操作',
                'game_over': '游戏结束'
            }
            
            info_text = f"状态: {state_text.get(game_state['state'], game_state['state'])}"
            if game_state['state'] == 'playing':
                current_player_info = self.game_engine.get_player_info(game_state['current_player'])
                if current_player_info:
                    info_text += f" | 当前玩家: {current_player_info['name']}"
            
            info_text += f" | 剩余牌数: {game_state['remaining_tiles']}"
            
            self.root.after(0, lambda: self.game_info_var.set(info_text))
            
            # 更新手牌显示
            human_player = self.get_human_player()
            if human_player:
                self.root.after(0, lambda: self.update_hand_tiles(human_player))
            
        except Exception as e:
            print(f"更新游戏显示错误: {e}")
    
    def update_ui(self):
        """更新用户界面（保持兼容性）"""
        self.update_game_display()
    
    def update_hand_tiles(self, player: Player = None):
        """更新手牌"""
        for btn in self.tile_buttons:
            btn.destroy()
        self.tile_buttons.clear()
        
        if not player:
            player = self.get_human_player()
        if not player:
            return
        
        for tile in player.hand_tiles:
            is_selected = (tile == self.selected_tile)
            btn = tk.Button(self.hand_frame, text=str(tile), width=4,
                          bg="#3498db" if is_selected else "#ecf0f1",
                          command=lambda t=tile: self.select_tile(t))
            btn.pack(side=tk.LEFT, padx=2)
            self.tile_buttons.append(btn)
    
    def on_tile_exchange_start(self, direction: int):
        """处理换三张开始事件"""
        direction_text = "顺时针" if direction == 1 else "逆时针"
        self.add_message(f"换三张阶段开始，方向: {direction_text}")
        
        # 在主线程中显示换三张窗口
        self.root.after(0, self.show_tile_exchange_window)
    
    def show_tile_exchange_window(self):
        """显示换三张窗口"""
        if self.exchange_window:
            return
        
        self.exchange_window = tk.Toplevel(self.root)
        self.exchange_window.title("换三张")
        self.exchange_window.geometry("600x400")
        self.exchange_window.resizable(False, False)
        
        # 使窗口居中
        self.exchange_window.transient(self.root)
        self.exchange_window.grab_set()
        
        # 说明文字
        instruction_label = ttk.Label(
            self.exchange_window, 
            text="请选择三张同花色的牌进行交换：",
            font=("Arial", 12)
        )
        instruction_label.pack(pady=10)
        
        # 手牌显示区域
        hand_frame = ttk.Frame(self.exchange_window)
        hand_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.exchange_canvas = tk.Canvas(hand_frame, bg='white', height=200)
        self.exchange_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 选中牌显示区域
        selected_frame = ttk.LabelFrame(self.exchange_window, text="已选择的牌")
        selected_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.selected_label = ttk.Label(selected_frame, text="未选择")
        self.selected_label.pack(pady=5)
        
        # 按钮区域
        button_frame = ttk.Frame(self.exchange_window)
        button_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Button(button_frame, text="确认交换", 
                  command=self.confirm_tile_exchange).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="重新选择", 
                  command=self.reset_tile_selection).pack(side=tk.RIGHT, padx=5)
        
        # 初始化选择
        self.selected_exchange_tiles = []
        self.update_exchange_display()
    
    def update_exchange_display(self):
        """更新换三张显示"""
        if not self.exchange_canvas:
            return
        
        self.exchange_canvas.delete("all")
        
        human_player = self.get_human_player()
        if not human_player or not human_player.hand_tiles:
            return
        
        # 按花色分组显示
        suits = {}
        for tile in human_player.hand_tiles:
            if tile.tile_type not in suits:
                suits[tile.tile_type] = []
            suits[tile.tile_type].append(tile)
        
        canvas_width = self.exchange_canvas.winfo_width()
        if canvas_width <= 1:
            self.root.after(100, self.update_exchange_display)
            return
        
        tile_width = 35
        tile_height = 50
        spacing = 3
        row_height = 70
        
        y_offset = 10
        for suit_type, tiles in suits.items():
            # 花色标题
            self.exchange_canvas.create_text(
                10, y_offset + 10, text=f"{suit_type.value}:",
                anchor=tk.W, font=("Arial", 10, "bold")
            )
            
            # 绘制该花色的牌
            x_offset = 60
            for tile in tiles:
                color = "lightgreen" if tile in self.selected_exchange_tiles else "white"
                
                rect_id = self.exchange_canvas.create_rectangle(
                    x_offset, y_offset, x_offset + tile_width, y_offset + tile_height,
                    fill=color, outline="black", width=1
                )
                
                text_id = self.exchange_canvas.create_text(
                    x_offset + tile_width // 2, y_offset + tile_height // 2,
                    text=str(tile.value), font=("Arial", 8)
                )
                
                # 绑定点击事件
                self.exchange_canvas.tag_bind(rect_id, "<Button-1>", 
                                            lambda e, t=tile: self.on_exchange_tile_click(t))
                self.exchange_canvas.tag_bind(text_id, "<Button-1>", 
                                            lambda e, t=tile: self.on_exchange_tile_click(t))
                
                x_offset += tile_width + spacing
            
            y_offset += row_height
        
        # 更新选中牌显示
        if self.selected_exchange_tiles:
            selected_text = " ".join([str(t) for t in self.selected_exchange_tiles])
            self.selected_label.config(text=f"已选择: {selected_text}")
        else:
            self.selected_label.config(text="未选择")
    
    def on_exchange_tile_click(self, tile: Tile):
        """处理换牌选择点击"""
        if tile in self.selected_exchange_tiles:
            self.selected_exchange_tiles.remove(tile)
        else:
            if len(self.selected_exchange_tiles) < 3:
                # 检查是否同花色
                if not self.selected_exchange_tiles or tile.tile_type == self.selected_exchange_tiles[0].tile_type:
                    self.selected_exchange_tiles.append(tile)
                else:
                    messagebox.showwarning("提示", "请选择同花色的牌！")
            else:
                messagebox.showwarning("提示", "最多只能选择3张牌！")
        
        self.update_exchange_display()
    
    def reset_tile_selection(self):
        """重置牌选择"""
        self.selected_exchange_tiles = []
        self.update_exchange_display()
    
    def confirm_tile_exchange(self):
        """确认换牌"""
        if len(self.selected_exchange_tiles) != 3:
            messagebox.showwarning("提示", "请选择3张牌！")
            return
        
        human_player = self.get_human_player()
        if not human_player:
            return
        
        # 提交换牌选择
        success = self.game_engine.submit_exchange_tiles(human_player.player_id, self.selected_exchange_tiles)
        if success:
            self.add_message(f"已提交换牌: {[str(t) for t in self.selected_exchange_tiles]}")
            self.exchange_window.destroy()
            self.exchange_window = None
        else:
            messagebox.showerror("错误", "换牌提交失败！")
    
    def on_missing_suit_selection_start(self):
        """处理选择缺一门开始事件"""
        self.add_message("请选择缺一门...")
        
        # 在主线程中显示选择窗口
        self.root.after(0, self.show_missing_suit_window)
    
    def show_missing_suit_window(self):
        """显示选择缺一门窗口"""
        if self.missing_suit_window:
            return
        
        self.missing_suit_window = tk.Toplevel(self.root)
        self.missing_suit_window.title("选择缺一门")
        self.missing_suit_window.geometry("300x200")
        self.missing_suit_window.resizable(False, False)
        
        # 使窗口居中
        self.missing_suit_window.transient(self.root)
        self.missing_suit_window.grab_set()
        
        # 说明文字
        instruction_label = ttk.Label(
            self.missing_suit_window, 
            text="请选择要缺少的花色：",
            font=("Arial", 12)
        )
        instruction_label.pack(pady=20)
        
        # 选择按钮
        button_frame = ttk.Frame(self.missing_suit_window)
        button_frame.pack(pady=20)
        
        suits = [
            (TileType.WAN, "万"),
            (TileType.TONG, "筒"),
            (TileType.TIAO, "条")
        ]
        
        for suit_type, suit_name in suits:
            ttk.Button(
                button_frame, 
                text=f"缺{suit_name}",
                command=lambda s=suit_type: self.select_missing_suit(s)
            ).pack(side=tk.LEFT, padx=10)
    
    def select_missing_suit(self, suit: TileType):
        """选择缺一门"""
        human_player = self.get_human_player()
        if not human_player:
            return
        
        success = self.game_engine.submit_missing_suit(human_player.player_id, suit)
        if success:
            self.add_message(f"已选择缺{suit.value}")
            self.missing_suit_window.destroy()
            self.missing_suit_window = None
        else:
            messagebox.showerror("错误", "选择缺一门失败！")
    
    def add_message(self, message: str):
        """添加消息到消息区域"""
        def _add():
            self.message_text.insert(tk.END, f"{message}\n")
            self.message_text.see(tk.END)
        
        self.root.after(0, _add)
    
    def update_action_buttons(self):
        """更新操作按钮"""
        for btn in self.action_buttons.values():
            btn.config(state='disabled')
        
        human_player = self.game_engine.get_human_player()
        if not human_player or self.game_engine.state != GameState.PLAYING:
            return
        
        # 检查可用动作
        if self.game_engine.last_discarded_tile:
            if self.game_engine.can_player_action(human_player, GameAction.WIN):
                self.action_buttons["win"].config(state='normal')
            if self.game_engine.can_player_action(human_player, GameAction.PENG):
                self.action_buttons["peng"].config(state='normal')
            if self.game_engine.can_player_action(human_player, GameAction.GANG):
                self.action_buttons["gang"].config(state='normal')
            if self.game_engine.can_player_action(human_player, GameAction.CHI):
                self.action_buttons["chi"].config(state='normal')
            self.action_buttons["pass"].config(state='normal')
    
    def select_tile(self, tile: Tile):
        """选择手牌"""
        human_player = self.game_engine.get_human_player()
        current_player = self.game_engine.get_current_player()
        
        if not human_player or current_player != human_player:
            return
        
        if self.selected_tile == tile:
            # 打出选中的牌
            if self.game_engine.can_player_action(human_player, GameAction.DISCARD, tile):
                self.game_engine.execute_player_action(human_player, GameAction.DISCARD, tile)
                self.selected_tile = None
                self.update_ui()
                self.schedule_ai_turn()
        else:
            self.selected_tile = tile
            self.update_hand_tiles()
    
    def execute_action(self, action: str):
        """执行动作"""
        human_player = self.game_engine.get_human_player()
        if not human_player:
            return
        
        if action == "pass":
            self.update_ui()
            self.schedule_ai_turn()
            return
        
        game_action = GameAction(action)
        if self.game_engine.execute_player_action(human_player, game_action):
            self.update_ui()
            if not self.game_engine.is_game_over():
                self.schedule_ai_turn()
    
    def schedule_ai_turn(self):
        """安排AI回合"""
        def ai_turn():
            time.sleep(1)
            current_player = self.game_engine.get_current_player()
            if current_player and current_player.player_type != PlayerType.HUMAN:
                # 简单AI：随机选择可打的牌
                import random
                available_tiles = [t for t in current_player.hand_tiles 
                                 if self.game_engine.rule and self.game_engine.rule.can_discard(current_player, t)]
                if available_tiles:
                    tile = random.choice(available_tiles)
                    self.game_engine.execute_player_action(current_player, GameAction.DISCARD, tile)
                
                self.root.after(0, self.update_ui)
                if not self.game_engine.is_game_over():
                    next_player = self.game_engine.get_current_player()
                    if next_player and next_player.player_type != PlayerType.HUMAN:
                        self.root.after(2000, lambda: threading.Thread(target=ai_turn, daemon=True).start())
        
        threading.Thread(target=ai_turn, daemon=True).start()
    
    def return_to_menu(self):
        """返回主菜单"""
        if messagebox.askokcancel("返回主菜单", "确定返回主菜单吗？"):
            from .main_menu import MainMenu
            MainMenu(self.root, self.game_engine)
    
    def on_game_state_changed(self, state: GameState):
        """游戏状态变化"""
        self.update_ui()
    
    def on_player_action(self, player: Player, action: GameAction, data=None):
        """玩家动作"""
        self.update_ui()
    
    def on_game_over(self, winner: Player, scores: Dict):
        """游戏结束"""
        self.update_ui()
        result = f"游戏结束！\n获胜者: {winner.name}\n\n得分:\n"
        for name, score in scores.items():
            result += f"{name}: {score:+d}分\n"
        messagebox.showinfo("游戏结束", result) 