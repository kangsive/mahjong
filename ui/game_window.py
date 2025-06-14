# -*- coding: utf-8 -*-
"""
游戏窗口界面
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, Dict
import threading
import time

from game.game_engine import GameEngine, GameState, GameAction
from game.tile import Tile, TileType
from game.player import Player, PlayerType
from utils.font_config import font_config

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
        
        # 窗口状态
        self.is_active = True
        self.update_job = None
        self.last_update_state = None  # 用于减少闪烁
        
        self.setup_ui()
        self.setup_game_events()
        
        # 设置窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        
        # 使用定时器定期更新，而不是无限循环线程
        self.start_periodic_update()
        
    def setup_ui(self):
        """设置用户界面"""
        # 清除现有内容
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部信息栏
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 游戏信息
        info_frame = ttk.LabelFrame(top_frame, text="游戏信息", padding="5")
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.game_info_var = tk.StringVar()
        self.game_info_var.set("状态: 等待开始 | 剩余牌数: 0")
        ttk.Label(info_frame, textvariable=self.game_info_var).pack()
        
        # 当前玩家状态
        self.player_status_var = tk.StringVar()
        self.player_status_var.set("等待游戏开始...")
        ttk.Label(info_frame, textvariable=self.player_status_var, foreground="blue").pack(pady=(2, 0))
        
        # 四个玩家状态栏
        players_frame = ttk.LabelFrame(main_frame, text="玩家状态", padding="10")
        players_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 创建2x2网格显示四个玩家
        self.player_status_frames = {}
        self.player_status_vars = {}
        
        # 玩家布局：
        # 北(对面)  东(右边)
        # 西(左边)  南(自己)
        positions = [
            ("南 (玩家)", 1, 1),    # 玩家自己在下方
            ("东 (AI-1)", 1, 0),   # AI-1在右边
            ("北 (AI-2)", 0, 1),   # AI-2在对面
            ("西 (AI-3)", 0, 0)    # AI-3在左边
        ]
        
        for i, (pos_name, row, col) in enumerate(positions):
            frame = ttk.LabelFrame(players_frame, text=pos_name, padding="5")
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            
            # 玩家详细信息
            info_var = tk.StringVar()
            info_var.set("手牌: 0张 | 明牌: 无 | 缺门: 未选择")
            ttk.Label(frame, textvariable=info_var, font=("Arial", 9)).pack()
            
            # 当前状态
            status_var = tk.StringVar()
            status_var.set("等待中...")
            status_label = ttk.Label(frame, textvariable=status_var, foreground="gray")
            status_label.pack()
            
            self.player_status_frames[i] = frame
            self.player_status_vars[i] = {
                'info': info_var,
                'status': status_var,
                'label': status_label
            }
        
        # 配置网格权重
        players_frame.grid_columnconfigure(0, weight=1)
        players_frame.grid_columnconfigure(1, weight=1)
        
        # 中央区域 - 公共出牌池
        center_frame = ttk.LabelFrame(main_frame, text="出牌池", padding="10")
        center_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 出牌池显示区域（使用Canvas来支持滚动）
        canvas_frame = ttk.Frame(center_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.discard_canvas = tk.Canvas(canvas_frame, height=120, bg="lightgray")
        scrollbar_h = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.discard_canvas.xview)
        self.discard_canvas.configure(xscrollcommand=scrollbar_h.set)
        
        self.discard_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        scrollbar_h.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 手牌区域
        self.hand_frame = ttk.LabelFrame(main_frame, text="手牌", padding="10")
        self.hand_frame.pack(fill=tk.X, pady=10)
        
        # 操作按钮区域
        action_frame = ttk.LabelFrame(main_frame, text="操作", padding="10")
        action_frame.pack(fill=tk.X, pady=10)
        
        # 第一行：游戏操作按钮
        game_actions_frame = ttk.Frame(action_frame)
        game_actions_frame.pack(fill=tk.X, pady=(0, 5))
        
        actions = [("胡牌", "win"), ("杠", "gang"), ("碰", "peng"), ("过", "pass")]
        for text, action in actions:
            btn = ttk.Button(game_actions_frame, text=text, width=8,
                           command=lambda a=action: self.execute_action(a))
            btn.pack(side=tk.LEFT, padx=5)
            self.action_buttons[action] = btn
        
        # 第二行：出牌和控制按钮
        control_frame = ttk.Frame(action_frame)
        control_frame.pack(fill=tk.X)
        
        # 出牌按钮（左侧）
        discard_frame = ttk.Frame(control_frame)
        discard_frame.pack(side=tk.LEFT)
        
        self.discard_btn = ttk.Button(discard_frame, text="出牌", width=10, 
                                    command=self.discard_selected_tile, state='disabled')
        self.discard_btn.pack(side=tk.LEFT, padx=5)
        ttk.Label(discard_frame, text="(先选择手牌)", foreground="gray").pack(side=tk.LEFT, padx=5)
        
        # 控制按钮（右侧）
        main_control_frame = ttk.Frame(control_frame)
        main_control_frame.pack(side=tk.RIGHT)
        ttk.Button(main_control_frame, text="开始游戏", command=self.start_game).pack(side=tk.LEFT, padx=5)
        ttk.Button(main_control_frame, text="返回主菜单", command=self.return_to_menu).pack(side=tk.LEFT, padx=5)
        
        # 训练模式建议
        if self.is_training_mode:
            advice_frame = ttk.LabelFrame(main_frame, text="AI建议", padding="10")
            advice_frame.pack(fill=tk.BOTH, expand=True, pady=10)
            self.advice_text = tk.Text(advice_frame, height=4, wrap=tk.WORD)
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
        # 设置游戏引擎回调
        self.game_engine.on_ai_turn_start = self.on_ai_turn_start
        
        # 为人类玩家设置事件回调
        human_player = self.get_human_player()
        if human_player:
            # 换三张事件
            human_player.on_tile_exchange_start = self.on_tile_exchange_start
            # 选择缺一门事件
            human_player.on_missing_suit_selection_start = self.on_missing_suit_selection_start
    
    def start_periodic_update(self):
        """启动定期更新"""
        if self.is_active:
            try:
                self.update_game_display()
            except Exception as e:
                print(f"更新游戏显示错误: {e}")
            
            # 每800ms更新一次，减少频率避免闪烁
            self.update_job = self.root.after(800, self.start_periodic_update)
    
    def on_window_close(self):
        """窗口关闭处理"""
        self.is_active = False
        if self.update_job:
            self.root.after_cancel(self.update_job)
        self.return_to_menu()
    
    def start_game(self):
        """开始游戏"""
        try:
            # 重新设置事件回调（确保玩家已经创建）
            self.setup_game_events()
            
            success = self.game_engine.start_game()
            if success:
                self.add_message("🎮 游戏开始！正在发牌...")
                self.add_message("📋 游戏流程：发牌 → 换三张 → 选择缺门 → 开始打牌")
                # 立即更新一次显示
                self.update_game_display()
            else:
                messagebox.showerror("错误", "游戏启动失败！")
        except Exception as e:
            messagebox.showerror("错误", f"游戏启动失败: {e}")
    
    def get_human_player(self) -> Optional[Player]:
        """获取人类玩家"""
        try:
            if not self.game_engine or not self.game_engine.players:
                return None
            for player in self.game_engine.players:
                if player.player_type == PlayerType.HUMAN:
                    return player
            return None
        except Exception as e:
            print(f"获取人类玩家错误: {e}")
            return None
    
    def update_game_display(self):
        """更新游戏显示"""
        if not self.is_active:
            return
            
        try:
            # 检查UI组件是否仍然有效
            if not self.game_info_var:
                return
            
            # 获取游戏状态
            game_state = self.game_engine.get_game_state()
            current_state = (game_state.get('state'), game_state.get('current_player'))
            
            # 只有状态真正改变时才更新UI，减少闪烁
            if self.last_update_state != current_state:
                self.last_update_state = current_state
                
                # 更新游戏信息
                state_text = {
                    'waiting': '等待开始',
                    'dealing': '发牌中',
                    'tile_exchange': '换三张阶段',
                    'missing_suit_selection': '选择缺一门',
                    'playing': '游戏进行中',
                    'waiting_action': '等待操作',
                    'game_over': '游戏结束'
                }
                
                info_text = f"状态: {state_text.get(game_state.get('state', 'waiting'), '未知状态')}"
                info_text += f" | 剩余牌数: {game_state.get('remaining_tiles', 0)}"
                info_text += f" | 第{game_state.get('round_number', 0)}局"
                self.game_info_var.set(info_text)
                
                # 更新玩家状态
                self.update_player_status()
                
                # 更新玩家状态栏
                self.update_all_player_status()
                
                # 更新出牌池
                self.update_discard_pool()
                
                # 更新手牌显示
                self.update_hand_tiles()
                
                # 更新操作按钮
                self.update_action_buttons()
            
            # 始终更新玩家状态栏和出牌池，即使状态未改变（如手牌数量变化）
            self.update_all_player_status()
            self.update_discard_pool()
            
        except Exception as e:
            print(f"更新游戏显示错误: {e}")
    
    def update_player_status(self):
        """更新玩家状态显示"""
        try:
            game_state = self.game_engine.get_game_state()
            state = game_state.get('state', 'waiting')
            
            if state == 'waiting':
                self.player_status_var.set("点击'开始游戏'按钮开始")
            elif state == 'dealing':
                self.player_status_var.set("🎯 正在发牌，请等待...")
            elif state == 'tile_exchange':
                self.player_status_var.set("🔄 请选择三张同花色的牌进行交换")
            elif state == 'missing_suit_selection':
                self.player_status_var.set("🎲 请选择要缺少的花色（万、筒、条）")
            elif state == 'playing':
                current_player_index = game_state.get('current_player', 0)
                current_player_info = self.game_engine.get_player_info(current_player_index)
                
                if current_player_info:
                    human_player = self.get_human_player()
                    if current_player_info['name'] == (human_player.name if human_player else ''):
                        self.player_status_var.set("🎮 轮到你了！请选择手牌后点击'出牌'或选择其他操作")
                    else:
                        self.player_status_var.set(f"⏳ 等待 {current_player_info['name']} 出牌...")
                else:
                    self.player_status_var.set("🎮 游戏进行中...")
            elif state == 'game_over':
                self.player_status_var.set("🎉 游戏结束")
            else:
                self.player_status_var.set(f"状态: {state}")
                
        except Exception as e:
            print(f"更新玩家状态错误: {e}")
            self.player_status_var.set("状态更新错误")
    
    def update_all_player_status(self):
        """更新所有玩家状态栏"""
        try:
            if not hasattr(self.game_engine, 'players') or not self.game_engine.players:
                return
                
            for i in range(4):
                if i >= len(self.game_engine.players):
                    continue
                    
                player_info = self.game_engine.get_player_info(i)
                if not player_info or i not in self.player_status_vars:
                    continue
                
                # 更新玩家信息
                info_text = f"手牌: {player_info.get('hand_count', 0)}张"
                
                # 明牌信息
                melds = player_info.get('melds', [])
                if melds:
                    meld_strs = []
                    for meld in melds:
                        meld_type = meld.get('type', '未知')
                        tiles_count = len(meld.get('tiles', []))
                        meld_strs.append(f"{meld_type}({tiles_count})")
                    info_text += f" | 明牌: {', '.join(meld_strs)}"
                else:
                    info_text += " | 明牌: 无"
                
                # 缺门信息
                missing_suit = player_info.get('missing_suit')
                if missing_suit:
                    info_text += f" | 缺门: {missing_suit.value if hasattr(missing_suit, 'value') else missing_suit}"
                else:
                    info_text += " | 缺门: 未选择"
                
                self.player_status_vars[i]['info'].set(info_text)
                
                # 更新状态
                if player_info.get('is_current', False):
                    if 'AI-' in player_info.get('name', ''):
                        self.player_status_vars[i]['status'].set("🤖 AI思考中...")
                        self.player_status_vars[i]['label'].config(foreground="red")
                    else:
                        self.player_status_vars[i]['status'].set("🎯 轮到你了！")
                        self.player_status_vars[i]['label'].config(foreground="blue")
                elif player_info.get('is_winner', False):
                    self.player_status_vars[i]['status'].set("🎉 已胡牌")
                    self.player_status_vars[i]['label'].config(foreground="green")
                else:
                    self.player_status_vars[i]['status'].set("⏳ 等待中...")
                    self.player_status_vars[i]['label'].config(foreground="gray")
                    
        except Exception as e:
            print(f"更新玩家状态栏错误: {e}")
    
    def update_discard_pool(self):
        """更新出牌池显示"""
        try:
            if not hasattr(self, 'discard_canvas'):
                return
            
            # 清空画布
            self.discard_canvas.delete("all")
            
            game_state = self.game_engine.get_game_state()
            discard_pool = game_state.get('discard_pool', [])
            
            if not discard_pool:
                self.discard_canvas.create_text(10, 60, text="暂无出牌", anchor="w", fill="gray")
                return
            
            # 显示出牌，每张牌占用的宽度
            tile_width = 60
            x_offset = 10
            y_pos = 60
            
            for i, (tile, player_name) in enumerate(discard_pool):
                x_pos = x_offset + i * tile_width
                
                # 绘制牌的背景
                self.discard_canvas.create_rectangle(x_pos, y_pos-20, x_pos+50, y_pos+20, 
                                                   fill="white", outline="black")
                
                # 显示牌的内容
                self.discard_canvas.create_text(x_pos+25, y_pos-5, 
                                              text=str(tile), anchor="center", 
                                              font=("Arial", 10, "bold"))
                
                # 显示出牌的玩家
                self.discard_canvas.create_text(x_pos+25, y_pos+10, 
                                              text=player_name, anchor="center", 
                                              font=("Arial", 8), fill="blue")
            
            # 更新滚动区域
            self.discard_canvas.configure(scrollregion=self.discard_canvas.bbox("all"))
            
            # 自动滚动到最右边（最新的牌）
            if discard_pool:
                self.discard_canvas.xview_moveto(1.0)
                
        except Exception as e:
            print(f"更新出牌池错误: {e}")
    
    def update_ui(self):
        """更新用户界面（保持兼容性）"""
        self.update_game_display()
    
    def update_hand_tiles(self, player: Player = None):
        """更新手牌"""
        if not self.is_active:
            return
            
        try:
            # 清理现有按钮
            for btn in self.tile_buttons:
                if btn.winfo_exists():
                    btn.destroy()
            self.tile_buttons.clear()
            
            if not player:
                player = self.get_human_player()
            if not player or not player.hand_tiles:
                return
            
            # 创建手牌按钮
            for i, tile in enumerate(player.hand_tiles):
                try:
                    is_selected = (tile == self.selected_tile)
                    btn = tk.Button(self.hand_frame, text=str(tile), width=4, height=2,
                                  bg="#3498db" if is_selected else "#ecf0f1",
                                  fg="white" if is_selected else "black",
                                  font=("Arial", 8, "bold"),
                                  command=lambda t=tile: self.select_tile(t))
                    btn.pack(side=tk.LEFT, padx=2, pady=2)
                    self.tile_buttons.append(btn)
                except Exception as e:
                    print(f"创建手牌按钮错误: {e}")
                    break
            
            # 更新出牌按钮状态
            self.update_discard_button()
                    
        except Exception as e:
            print(f"更新手牌错误: {e}")
    
    def update_discard_button(self):
        """更新出牌按钮状态"""
        try:
            human_player = self.get_human_player()
            current_player = self.game_engine.get_current_player()
            
            # 只有轮到人类玩家且选择了牌时才能出牌
            can_discard = (human_player and 
                         current_player == human_player and 
                         self.selected_tile and
                         self.game_engine.state == GameState.PLAYING and
                         self.game_engine.can_player_action(human_player, GameAction.DISCARD, self.selected_tile))
            
            self.discard_btn.config(state='normal' if can_discard else 'disabled')
            
        except Exception as e:
            print(f"更新出牌按钮错误: {e}")
    
    def discard_selected_tile(self):
        """出牌"""
        if not self.selected_tile:
            messagebox.showwarning("提示", "请先选择要出的牌！")
            return
        
        human_player = self.get_human_player()
        if not human_player:
            return
        
        if self.game_engine.can_player_action(human_player, GameAction.DISCARD, self.selected_tile):
            success = self.game_engine.execute_player_action(human_player, GameAction.DISCARD, self.selected_tile)
            if success:
                self.add_message(f"🎯 你打出了: {self.selected_tile}")
                self.selected_tile = None
                self.update_game_display()
                self.schedule_ai_turn()
            else:
                messagebox.showerror("错误", "出牌失败！")
        else:
            messagebox.showwarning("提示", "现在不能出这张牌！")
    
    def on_tile_exchange_start(self, direction: int):
        """处理换三张开始事件"""
        direction_text = "顺时针" if direction == 1 else "逆时针"
        self.add_message(f"🔄 换三张阶段开始，方向: {direction_text}")
        self.add_message("💡 请选择三张同花色的牌进行交换")
        
        # 在主线程中显示换三张窗口
        self.root.after(0, self.show_tile_exchange_window)
    
    def show_tile_exchange_window(self):
        """显示换三张窗口"""
        if self.exchange_window:
            return
        
        self.exchange_window = tk.Toplevel(self.root)
        self.exchange_window.title("换三张")
        self.exchange_window.geometry("700x450")
        self.exchange_window.resizable(False, False)
        
        # 使窗口居中
        self.exchange_window.transient(self.root)
        # 延迟设置grab，避免冲突
        self.root.after(100, lambda: self.exchange_window.grab_set() if self.exchange_window else None)
        
        # 说明文字
        instruction_label = ttk.Label(
            self.exchange_window, 
            text="请选择三张同花色的牌进行交换（点击牌进行选择）：",
            font=("Arial", 12)
        )
        instruction_label.pack(pady=10)
        
        # 手牌显示区域
        hand_frame = ttk.Frame(self.exchange_window)
        hand_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.exchange_canvas = tk.Canvas(hand_frame, bg='white', height=250)
        self.exchange_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 选中牌显示区域
        selected_frame = ttk.LabelFrame(self.exchange_window, text="已选择的牌")
        selected_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.selected_label = ttk.Label(selected_frame, text="未选择", font=("Arial", 10))
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
        # 延迟调用更新显示，确保canvas已经初始化
        self.root.after(100, self.update_exchange_display)
    
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
        
        # 等待canvas初始化
        canvas_width = self.exchange_canvas.winfo_width()
        if canvas_width <= 1:
            self.root.after(100, self.update_exchange_display)
            return
        
        tile_width = 40
        tile_height = 60
        spacing = 5
        row_height = 80
        
        y_offset = 20
        for suit_type, tiles in suits.items():
            # 花色标题
            self.exchange_canvas.create_text(
                10, y_offset + 15, text=f"{suit_type.value}:",
                anchor=tk.W, font=("Arial", 12, "bold")
            )
            
            # 绘制该花色的牌
            x_offset = 70
            for tile in tiles:
                is_selected = tile in self.selected_exchange_tiles
                color = "lightgreen" if is_selected else "lightblue"
                
                rect_id = self.exchange_canvas.create_rectangle(
                    x_offset, y_offset, x_offset + tile_width, y_offset + tile_height,
                    fill=color, outline="black", width=2 if is_selected else 1
                )
                
                text_id = self.exchange_canvas.create_text(
                    x_offset + tile_width // 2, y_offset + tile_height // 2,
                    text=str(tile.value), font=("Arial", 10, "bold")
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
            self.selected_label.config(text=f"已选择: {selected_text} ({len(self.selected_exchange_tiles)}/3)")
        else:
            self.selected_label.config(text="未选择 (0/3)")
    
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
            self.add_message(f"✅ 已提交换牌: {[str(t) for t in self.selected_exchange_tiles]}")
            self.add_message("⏳ 等待其他玩家完成换牌...")
            self.exchange_window.destroy()
            self.exchange_window = None
        else:
            messagebox.showerror("错误", "换牌提交失败！")
    
    def on_missing_suit_selection_start(self):
        """处理选择缺一门开始事件"""
        self.add_message("🎲 换牌完成！现在请选择缺一门...")
        
        # 在主线程中显示选择窗口
        self.root.after(0, self.show_missing_suit_window)
    
    def show_missing_suit_window(self):
        """显示选择缺一门窗口"""
        if self.missing_suit_window:
            return
        
        self.missing_suit_window = tk.Toplevel(self.root)
        self.missing_suit_window.title("选择缺一门")
        self.missing_suit_window.geometry("400x300")
        self.missing_suit_window.resizable(False, False)
        
        # 使窗口居中
        self.missing_suit_window.transient(self.root)
        # 延迟设置grab，避免冲突
        self.root.after(100, lambda: self.missing_suit_window.grab_set() if self.missing_suit_window else None)
        
        # 说明文字
        instruction_label = ttk.Label(
            self.missing_suit_window, 
            text="请选择要缺少的花色：",
            font=("Arial", 14, "bold")
        )
        instruction_label.pack(pady=20)
        
        # 规则说明
        rule_text = ttk.Label(
            self.missing_suit_window,
            text="四川麻将规则：每位玩家必须选择缺少万、筒、条中的一门\n胡牌时手中不能有缺门的牌",
            font=("Arial", 10),
            foreground="gray"
        )
        rule_text.pack(pady=10)
        
        # 显示当前手牌统计
        human_player = self.get_human_player()
        if human_player:
            suit_counts = {"万": 0, "筒": 0, "条": 0}
            for tile in human_player.hand_tiles:
                if tile.tile_type.value in suit_counts:
                    suit_counts[tile.tile_type.value] += 1
            
            stats_text = "当前手牌统计：\n"
            for suit, count in suit_counts.items():
                stats_text += f"{suit}: {count}张  "
            
            stats_label = ttk.Label(
                self.missing_suit_window,
                text=stats_text,
                font=("Arial", 10),
                foreground="blue"
            )
            stats_label.pack(pady=10)
        
        # 选择按钮
        button_frame = ttk.Frame(self.missing_suit_window)
        button_frame.pack(pady=20)
        
        suits = [
            (TileType.WAN, "万"),
            (TileType.TONG, "筒"), 
            (TileType.TIAO, "条")
        ]
        
        for suit_type, suit_name in suits:
            btn = ttk.Button(
                button_frame, 
                text=f"缺{suit_name}",
                width=12,
                command=lambda s=suit_type: self.select_missing_suit(s)
            )
            btn.pack(side=tk.LEFT, padx=10)
    
    def select_missing_suit(self, suit: TileType):
        """选择缺一门"""
        human_player = self.get_human_player()
        if not human_player:
            return
        
        success = self.game_engine.submit_missing_suit(human_player.player_id, suit)
        if success:
            self.add_message(f"✅ 已选择缺{suit.value}")
            self.add_message("⏳ 等待其他玩家完成选择...")
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
        try:
            # 默认禁用所有按钮
            for btn in self.action_buttons.values():
                btn.config(state='disabled')
            
            human_player = self.get_human_player()
            if not human_player or self.game_engine.state != GameState.PLAYING:
                return
            
            # 检查可用动作
            if self.game_engine.last_discarded_tile and self.game_engine.last_discard_player != human_player:
                # 有人刚打牌，检查可以执行的动作
                if self.game_engine.can_player_action(human_player, GameAction.WIN):
                    self.action_buttons["win"].config(state='normal')
                if self.game_engine.can_player_action(human_player, GameAction.PENG):
                    self.action_buttons["peng"].config(state='normal')
                if self.game_engine.can_player_action(human_player, GameAction.GANG):
                    self.action_buttons["gang"].config(state='normal')
                # 四川麻将不能吃牌
                # if self.game_engine.can_player_action(human_player, GameAction.CHI):
                #     self.action_buttons["chi"].config(state='normal')
                
                # 总是可以选择过
                self.action_buttons["pass"].config(state='normal')
            
            # 轮到玩家时，可以自摸胡牌
            elif self.game_engine.get_current_player() == human_player:
                if self.game_engine.rule.can_win(human_player):
                    self.action_buttons["win"].config(state='normal')
                    
        except Exception as e:
            print(f"更新操作按钮错误: {e}")
    
    def select_tile(self, tile: Tile):
        """选择手牌"""
        human_player = self.get_human_player()
        current_player = self.game_engine.get_current_player()
        
        if not human_player:
            return
        
        # 只有轮到人类玩家时才能选择牌
        if current_player != human_player:
            self.add_message("⚠️ 现在不是你的回合！")
            return
        
        # 切换选择状态
        if self.selected_tile == tile:
            # 取消选择
            self.selected_tile = None
        else:
            # 选择新牌
            self.selected_tile = tile
            self.add_message(f"已选择: {tile}")
        
        # 更新显示
        self.update_hand_tiles()
        self.update_discard_button()
    
    def execute_action(self, action: str):
        """执行动作"""
        human_player = self.get_human_player()
        if not human_player:
            return
        
        if action == "pass":
            self.add_message("🔄 你选择了过牌")
            # 如果有其他玩家打牌，清除相关状态并继续游戏
            if self.game_engine.last_discarded_tile:
                self.game_engine.last_discarded_tile = None
                self.game_engine.last_discard_player = None
                # 继续下一个玩家
                self.game_engine._next_player()
            self.update_game_display()
            self.schedule_ai_turn()
            return
        
        try:
            game_action = GameAction(action)
            success = self.game_engine.execute_player_action(human_player, game_action)
            
            if success:
                action_names = {
                    "win": "胡牌",
                    "gang": "杠",
                    "peng": "碰",
                    "chi": "吃"
                }
                self.add_message(f"✅ 你执行了: {action_names.get(action, action)}")
                self.update_game_display()
                
                if not self.game_engine.is_game_over():
                    self.schedule_ai_turn()
            else:
                self.add_message(f"❌ 无法执行 {action}")
                
        except Exception as e:
            print(f"执行动作错误: {e}")
            self.add_message(f"❌ 执行动作失败: {e}")
    
    def schedule_ai_turn(self):
        """安排AI回合"""
        def ai_turn():
            try:
                time.sleep(1)  # 模拟思考时间
                current_player = self.game_engine.get_current_player()
                
                if current_player and current_player.player_type != PlayerType.HUMAN:
                    # 导入AI模块
                    from ai.simple_ai import SimpleAI
                    
                    # 创建AI实例
                    ai = SimpleAI("medium" if current_player.player_type == PlayerType.AI_MEDIUM else "hard")
                    
                    # 检查是否可以胡牌
                    if self.game_engine.rule and self.game_engine.rule.can_win(current_player):
                        self.root.after(0, lambda: self.add_message(f"🎉 {current_player.name} 胡牌了！"))
                        success = self.game_engine.execute_player_action(current_player, GameAction.WIN)
                        if success:
                            self.root.after(0, self.update_game_display)
                            return
                    
                    # AI选择打牌
                    available_tiles = [t for t in current_player.hand_tiles 
                                     if self.game_engine.rule and self.game_engine.rule.can_discard(current_player, t)]
                    
                    if available_tiles:
                        # 使用AI算法选择出牌
                        tile_to_discard = ai.choose_discard(current_player, available_tiles)
                        
                        # 添加AI动作消息
                        self.root.after(0, lambda: self.add_message(f"🤖 {current_player.name} 打出了: {tile_to_discard}"))
                        
                        success = self.game_engine.execute_player_action(current_player, GameAction.DISCARD, tile_to_discard)
                        if success:
                            # 更新UI
                            self.root.after(0, self.update_game_display)
                            
                            # 检查游戏状态
                            if not self.game_engine.is_game_over():
                                # 根据游戏状态决定下一步
                                if self.game_engine.state == GameState.WAITING_ACTION:
                                    # 有玩家可以响应，等待响应
                                    self.root.after(1000, self.handle_ai_responses)
                                elif self.game_engine.state == GameState.PLAYING:
                                    # 继续下一个玩家
                                    next_player = self.game_engine.get_current_player()
                                    if next_player and next_player.player_type != PlayerType.HUMAN:
                                        # 继续AI回合
                                        self.root.after(2000, lambda: threading.Thread(target=ai_turn, daemon=True).start())
                        else:
                            # AI出牌失败，跳过
                            self.game_engine._next_player()
                            self.root.after(0, self.update_game_display)
                    else:
                        # 没有可出的牌，跳过
                        self.root.after(0, lambda: self.add_message(f"🤖 {current_player.name} 没有可出的牌"))
                        self.game_engine._next_player()
                        self.root.after(0, self.update_game_display)
                        
            except Exception as e:
                print(f"AI回合错误: {e}")
                self.root.after(0, lambda: self.add_message(f"AI操作出错: {e}"))
        
        # 只有不是人类玩家的回合才启动AI
        current_player = self.game_engine.get_current_player()
        if current_player and current_player.player_type != PlayerType.HUMAN:
            threading.Thread(target=ai_turn, daemon=True).start()
    
    def handle_ai_responses(self):
        """处理AI对出牌的响应（胡、碰、杠等）"""
        def ai_response():
            try:
                if self.game_engine.state != GameState.WAITING_ACTION:
                    return
                
                if not self.game_engine.last_discarded_tile:
                    return
                
                from ai.simple_ai import SimpleAI
                
                # 检查每个AI玩家的响应
                responded = False
                
                for player in self.game_engine.players:
                    if (player.player_type != PlayerType.HUMAN and 
                        player != self.game_engine.last_discard_player):
                        
                        ai = SimpleAI("medium" if player.player_type == PlayerType.AI_MEDIUM else "hard")
                        
                        # 检查可用动作
                        available_actions = []
                        if self.game_engine.rule.can_win(player, self.game_engine.last_discarded_tile):
                            available_actions.append(GameAction.WIN)
                        if player.can_gang(self.game_engine.last_discarded_tile):
                            available_actions.append(GameAction.GANG)
                        if player.can_peng(self.game_engine.last_discarded_tile):
                            available_actions.append(GameAction.PENG)
                        
                        if available_actions:
                            available_actions.append(GameAction.PASS)
                            
                            # AI决策
                            context = {
                                'last_discarded_tile': self.game_engine.last_discarded_tile,
                                'discard_player': self.game_engine.last_discard_player.name
                            }
                            
                            action = ai.decide_action(player, available_actions, context)
                            
                            if action and action != GameAction.PASS:
                                # AI选择执行动作
                                action_names = {
                                    GameAction.WIN: "胡牌",
                                    GameAction.GANG: "杠",
                                    GameAction.PENG: "碰"
                                }
                                
                                self.root.after(0, lambda a=action_names.get(action, "动作"), n=player.name: 
                                               self.add_message(f"🤖 {n} 选择了: {a}"))
                                
                                success = self.game_engine.execute_player_action(player, action)
                                if success:
                                    responded = True
                                    self.root.after(0, self.update_game_display)
                                    
                                    # 如果是杠或碰，轮到该玩家出牌
                                    if action in [GameAction.GANG, GameAction.PENG] and not self.game_engine.is_game_over():
                                        self.game_engine.state = GameState.PLAYING
                                        self.root.after(2000, lambda: threading.Thread(target=self.schedule_ai_turn, daemon=True).start())
                                    
                                    return
                
                # 如果没有AI响应，继续游戏
                if not responded:
                    self.game_engine.state = GameState.PLAYING
                    self.game_engine._next_player()
                    self.root.after(0, self.update_game_display)
                    
                    # 继续下一个玩家的回合
                    if not self.game_engine.is_game_over():
                        current_player = self.game_engine.get_current_player()
                        if current_player and current_player.player_type != PlayerType.HUMAN:
                            self.root.after(1000, lambda: threading.Thread(target=lambda: self.schedule_ai_turn(), daemon=True).start())
                    
            except Exception as e:
                print(f"处理AI响应错误: {e}")
                self.root.after(0, lambda: self.add_message(f"AI响应出错: {e}"))
        
        threading.Thread(target=ai_response, daemon=True).start()
    
    def return_to_menu(self):
        """返回主菜单"""
        self.is_active = False
        if self.update_job:
            self.root.after_cancel(self.update_job)
        
        # 关闭所有子窗口
        if self.exchange_window:
            self.exchange_window.destroy()
            self.exchange_window = None
        if self.missing_suit_window:
            self.missing_suit_window.destroy()
            self.missing_suit_window = None
        
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
        self.add_message(f"🎉 游戏结束！获胜者: {winner.name}")
        
        result = f"游戏结束！\n获胜者: {winner.name}\n\n得分:\n"
        for name, score in scores.items():
            result += f"{name}: {score:+d}分\n"
        messagebox.showinfo("游戏结束", result)
    
    def on_ai_turn_start(self, ai_player: Player):
        """AI回合开始回调"""
        self.add_message(f"🤖 {ai_player.name} 开始思考...")
        self.schedule_ai_turn() 