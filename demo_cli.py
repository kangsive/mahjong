#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麻将游戏命令行演示

用法:
  python3 demo_cli.py          # 静默模式，禁用所有日志输出
  python3 demo_cli.py --debug  # 调试模式，启用日志输出

注意: 默认情况下所有日志输出都被禁用，只有加上 --debug 标志才会显示日志
"""

import sys
import os
import time
import argparse
import logging

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='麻将游戏命令行演示')
    parser.add_argument('--debug', action='store_true', 
                       help='启用调试模式，显示日志输出')
    return parser.parse_args()

def configure_logging(debug_mode):
    """配置日志系统"""
    if not debug_mode:
        # 完全禁用所有日志输出
        logging.disable(logging.CRITICAL)
        # 禁用根logger和所有子logger
        root_logger = logging.getLogger()
        root_logger.disabled = True
        root_logger.setLevel(logging.CRITICAL + 1)
        
        # 禁用常见的logger名称
        for logger_name in ['mahjong_game', 'game_engine', 'utils.logger']:
            logger = logging.getLogger(logger_name)
            logger.disabled = True
            logger.setLevel(logging.CRITICAL + 1)
            # 移除所有handlers以防止任何输出
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
    else:
        # 启用日志输出
        logging.disable(logging.NOTSET)
        root_logger = logging.getLogger()
        root_logger.disabled = False
        root_logger.setLevel(logging.INFO)

# 解析命令行参数
args = parse_arguments()

# 在导入其他模块之前就配置日志
configure_logging(args.debug)

from game.game_engine import GameEngine, GameMode, GameAction
from game.player import PlayerType, Player
from game.tile import Tile, format_mahjong_tiles
from ai.trainer_ai import TrainerAI
from ai.shanten_ai import ShantenAI
from rules.sichuan_rule import SichuanRule
import random
from typing import List, Optional, Tuple

def set_terminal_font_size():
    """设置终端字体大小以便更好地显示麻将符号"""
    # 检测终端类型并设置字体大小
    if os.name == 'nt':  # Windows
        # Windows下设置控制台字体
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleOutputCP(65001)  # 设置UTF-8编码
            # 这里可以添加更多Windows特定的字体设置
        except:
            pass
    else:  # Unix/Linux/Mac
        # 设置终端字体大小（如果支持）
        try:
            # 清除任何背景色设置，保持终端默认背景
            print("\033[0m", end="")  # 重置所有格式
            # 不设置背景色，让终端保持默认背景
        except:
            pass

def format_large_mahjong_tile(tile, index=None, color_code=None):
    """格式化单个麻将牌为大字体显示"""
    if color_code is None:
        color_code = "1;97"  # 默认亮白色粗体
    
    symbol = str(tile)
    
    if index is not None:
        return f"\033[{color_code}m[{index}]{symbol}\033[0m"
    else:
        return f"\033[{color_code}m{symbol}\033[0m"

def format_large_mahjong_tiles(tiles, with_indices=True, color_scheme="default"):
    """格式化多个麻将牌为大字体显示"""
    if not tiles:
        return ""
    
    # 颜色方案 - 只使用前景色，不设置背景色
    color_schemes = {
        "default": "1;97",      # 亮白色粗体
        "hand": "1;93",         # 亮黄色粗体（手牌）
        "drawn": "1;92",        # 亮绿色粗体（摸到的牌）
        "discarded": "1;91",    # 亮红色粗体（打出的牌）
        "action": "1;95",       # 亮紫色粗体（动作相关）
        "ai": "1;94",          # 亮蓝色粗体（AI出牌）
        "meld": "1;96",        # 亮青色粗体（组合牌）
    }
    
    color_code = color_schemes.get(color_scheme, color_schemes["default"])
    
    formatted_tiles = []
    for i, tile in enumerate(tiles):
        if with_indices:
            formatted_tiles.append(format_large_mahjong_tile(tile, i+1, color_code))
        else:
            formatted_tiles.append(format_large_mahjong_tile(tile, None, color_code))
    
    return "  ".join(formatted_tiles)  # 使用双空格分隔以增加可读性

def reset_terminal_format():
    """重置终端格式，确保背景色一致"""
    print("\033[0m", end="")  # 重置所有格式
    # 不清屏，保持终端历史

def display_mahjong_banner():
    """显示麻将游戏横幅"""
    # 确保格式重置
    print("\033[0m", end="")
    print("\n" + "="*80)
    print("🀄 " + " "*30 + "麻将游戏" + " "*30 + " 🀄")
    print("="*80)

def display_game_status(engine):
    """显示游戏状态"""
    print("\n" + "="*60)
    status = engine.get_game_status()
    current_player = engine.get_current_player()
    
    print(f"🀄 麻将游戏 - 第{status['round_number']}局")
    print(f"游戏状态: {status['state']}")
    print(f"剩余牌数: {status['remaining_tiles']}")
    print(f"当前玩家: {current_player.name if current_player else '无'}")
    print("="*60)

def display_discard_pool(engine):
    """显示公共出牌池"""
    print("\n🌊 公共出牌池:")
    if not engine.discard_pool:
        print("   (空)")
        return
    
    # 使用新的格式化函数显示打出的牌
    discards_str = format_large_mahjong_tiles(engine.discard_pool, with_indices=False, color_scheme="discarded")
    print(f"   {discards_str}")

def display_player_info(engine):
    """显示所有玩家信息"""
    print("\n📊 玩家信息:")
    
    for i, player in enumerate(engine.players):
        status = ""
        # 使用 getattr 安全地访问 is_winner 属性
        if getattr(player, 'is_winner', False):
            status = "🏆 已胡牌!"
        elif player.can_win:
            status = "🎉 听牌!"

        print(f"\n{i+1}. {player.name} ({player.player_type.value}) {status}")
        
        # 已胡牌的玩家不再显示手牌数，只显示得分和组合
        if getattr(player, 'is_winner', False):
            print(f"   得分: {player.score}")
            if player.melds:
                print(f"   组合: {len(player.melds)}个")
                for meld in player.melds:
                    tiles_str = format_large_mahjong_tiles(meld.tiles, with_indices=False, color_scheme="meld")
                    print(f"     {meld.meld_type.value}: {tiles_str}")
            continue

        print(f"   手牌: {'🀫 ' * player.get_hand_count()}")
        print(f"   得分: {player.score}")
        
        # 临时调试：显示所有玩家的手牌
        if player.hand_tiles:
            hand_str = " ".join(str(tile) for tile in player.hand_tiles)
            print(f"   🃏 手牌: {hand_str}")
        
        if player.missing_suit:
            print(f"   缺门: {player.missing_suit}")
        
        if player.melds:
            print(f"   组合: {len(player.melds)}个")
            for meld in player.melds:
                tiles_str = format_large_mahjong_tiles(meld.tiles, with_indices=False, color_scheme="meld")
                print(f"     {meld.meld_type.value}: {tiles_str}")

def display_human_hand(engine):
    """显示人类玩家手牌"""
    human_player = engine.get_human_player()
    if not human_player:
        return
    
    # 显示刚摸到的牌
    if (hasattr(engine, 'last_drawn_tile') and engine.last_drawn_tile and 
        engine.get_current_player() == human_player):
        drawn_tile = format_large_mahjong_tile(engine.last_drawn_tile, color_code="1;32")
        print(f"\n💎 你刚摸到了: {drawn_tile}")

    print(f"\n🃏 {human_player.name}的手牌:")
    # 使用新的格式化函数显示手牌
    hand_str = format_large_mahjong_tiles(human_player.hand_tiles, with_indices=True, color_scheme="hand")
    print(f"   {hand_str}")
    


def get_ai_advice(engine):
    """获取AI建议"""
    if engine.mode != GameMode.TRAINING:
        return
    
    human_player = engine.get_human_player()
    if not human_player:
        return
    
    trainer = TrainerAI()
    is_sichuan = isinstance(engine.rule, SichuanRule)
    context = {
        "can_win": human_player.can_win,
        "last_discarded_tile": engine.last_discarded_tile,
        "is_your_turn": engine.get_current_player() == human_player,
        "is_sichuan_rule": is_sichuan # 添加规则信息
    }
    
    advice = trainer.provide_advice(human_player, context)
    
    if advice:
        # 在四川规则下，过滤掉关于"吃"的建议
        if is_sichuan and "吃" in advice:
            advice_lines = advice.split('\n')
            filtered_lines = [line for line in advice_lines if "吃" not in line]
            advice = "\n".join(filtered_lines).strip()

        if advice:
            print(f"\n🎓 AI训练师建议:")
            print(advice)

def simulate_human_turn(engine: GameEngine):
    """处理人类玩家的回合，获取用户输入"""
    human_player = engine.get_human_player()
    current_player = engine.get_current_player()

    if not human_player or current_player != human_player:
        return False

    # 检查是否可以自摸胡牌
    if engine.can_player_action(human_player, GameAction.WIN):
        print(f"\n🎉 恭喜！你可以自摸胡牌！")
        choice = input("是否胡牌？(y/n): ").strip().lower()
        if choice in ['y', 'yes', '是', '胡']:
            success = engine.execute_player_action(human_player, GameAction.WIN)
            if success:
                print(f"✅ {human_player.name} 自摸胡牌成功！")
                return True
            else:
                print(f"❌ 胡牌失败，继续出牌")
        else:
            print(f"选择不胡牌，继续出牌")

    # 检查是否可以暗杠
    hidden_gang_tiles = human_player.can_hidden_gang()
    if hidden_gang_tiles:
        print(f"\n🔥 你可以暗杠！")
        print("可暗杠的牌:")
        for i, tile in enumerate(hidden_gang_tiles):
            tile_display = format_large_mahjong_tile(tile, color_code="1;32")
            print(f"  {i+1}. {tile_display}")
        
        choice = input("选择要暗杠的牌序号，或输入 'n' 跳过: ").strip().lower()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(hidden_gang_tiles):
                tile_to_gang = hidden_gang_tiles[idx]
                success = engine.execute_player_action(human_player, GameAction.GANG, tile_to_gang)
                if success:
                    tile_display = format_large_mahjong_tile(tile_to_gang, color_code="1;32")
                    print(f"✅ 成功暗杠 {tile_display}")
                    return True
                else:
                    print(f"❌ 暗杠失败")
            else:
                print(f"序号无效")
        elif choice != 'n':
            print(f"输入无效，跳过暗杠")

    print(f"\n🎮 轮到{human_player.name}了! 请选择要打出的牌。")

    while True:
        try:
            choice_str = input(f"请输入要打出牌的序号 (1-{human_player.get_hand_count()}), 或输入 'q' 退出: ")
            if choice_str.lower() == 'q':
                return False

            choice_idx = int(choice_str) - 1
            if 0 <= choice_idx < human_player.get_hand_count():
                tile_to_discard = human_player.hand_tiles[choice_idx]
                
                if not engine.rule.can_discard(human_player, tile_to_discard):
                    tile_display = format_large_mahjong_tile(tile_to_discard, color_code="1;31")
                    print(f"🚫 规则不允许打出 {tile_display}。请优先打完缺牌。")
                    continue
                
                tile_display = format_large_mahjong_tile(tile_to_discard, color_code="1;33")
                print(f"你选择了打出: {tile_display}")
                success = engine.execute_player_action(human_player, GameAction.DISCARD, tile_to_discard)
                if success:
                    print(f"✅ 成功打出 {tile_display}")
                    return True
                else:
                    print("❌ 打牌失败，未知错误。")
                    return False
            else:
                print(f"序号无效，请输入1到{human_player.get_hand_count()}之间的数字。")
        except ValueError:
            print("输入无效，请输入一个数字。")
        except Exception as e:
            print(f"发生错误: {e}")
            return False

def simulate_ai_turn(engine: GameEngine):
    """模拟AI回合"""
    current_player = engine.get_current_player()
    
    if not current_player or current_player.player_type == PlayerType.HUMAN or getattr(current_player, 'is_winner', False):
        return False
    
    print(f"\n🤖 {current_player.name}思考中...")
    time.sleep(1)
    
    # 1. 检查自摸胡牌
    if engine.can_player_action(current_player, GameAction.WIN):
        print(f"🎉 {current_player.name} 决定自摸胡牌!")
        success = engine.execute_player_action(current_player, GameAction.WIN)
        if success:
            print(f"✅ {current_player.name} 自摸胡牌成功!")
            input("\n按回车键继续...")
            return True
        else:
            print(f"❌ {current_player.name} 尝试自摸失败，继续出牌。")

    # 2. 检查暗杠，使用AI决策
    hidden_gang_tiles = current_player.can_hidden_gang()
    if hidden_gang_tiles:
        # 使用AI算法决定是否暗杠
        should_gang, tile_to_gang = decide_hidden_gang_ai(current_player, hidden_gang_tiles, engine)
        if should_gang and tile_to_gang:
            print(f"🔥 {current_player.name} 决定暗杠!")
            success = engine.execute_player_action(current_player, GameAction.GANG, tile_to_gang)
            if success:
                print(f"✅ {current_player.name} 成功暗杠!")
                input("\n按回车键继续...")
                return True
            else:
                print(f"❌ {current_player.name} 暗杠失败，继续出牌。")

    # 3. 智能选择打牌
    available_tiles = [t for t in current_player.hand_tiles 
                      if engine.rule.can_discard(current_player, t)]
    
    if not available_tiles:
        print(f"⚠️ {current_player.name} 无牌可打，游戏可能卡住。")
        return False # 发出错误信号

    # 使用AI算法选择最优出牌
    tile_to_discard = choose_best_discard_ai(current_player, available_tiles, engine)
    print(f"即将打出: {tile_to_discard.value}{tile_to_discard.tile_type.value}")
    tile_display = format_large_mahjong_tile(tile_to_discard, color_code="1;34")
    print(f"\n🎯 {current_player.name}打出: {tile_display}")
    print("=" * 40)
    
    success = engine.execute_player_action(current_player, GameAction.DISCARD, tile_to_discard)
    if success:
        # 成功出牌后暂停，以便观察
        input("\n按回车键继续...")
        return True
    else:
        # 这是一个严重错误，意味着引擎状态不一致
        error_tile = format_large_mahjong_tile(tile_to_discard, color_code="1;31")
        print(f"❌ 严重错误: {current_player.name} 无法打出可选牌 {error_tile}.")
        print("   这通常是游戏引擎或规则的内部错误。")
        return False # 发出错误信号

def choose_best_discard_ai(player: Player, available_tiles: List[Tile], engine) -> Tile:
    """AI智能选择最优出牌"""
    # 使用引擎的统一AI创建方法
    ai = engine.create_ai_instance(player.player_type)
    
    if ai is None:
        # 如果AI创建失败，使用简单的随机选择作为后备
        import random
        return random.choice(available_tiles)
    
    # 使用AI算法选择出牌
    return ai.choose_discard(player, available_tiles)

def handle_ai_responses(engine: GameEngine, last_discarder=None):
    """检查并执行AI对出牌的响应动作"""
    if not engine.last_discarded_tile:
        return False

    actions = []
    # 收集所有AI玩家的可能动作
    for player in engine.players:
        if player == last_discarder or player.player_type == PlayerType.HUMAN or getattr(player, 'is_winner', False):
            continue

        # 使用AI算法决定是否执行动作
        available_actions = []
        if engine.can_player_action(player, GameAction.WIN):
            available_actions.append(GameAction.WIN)
        if engine.can_player_action(player, GameAction.GANG):
            available_actions.append(GameAction.GANG)
        if engine.can_player_action(player, GameAction.PENG):
            available_actions.append(GameAction.PENG)
        
        if available_actions:
            # 使用AI决策
            chosen_action = choose_best_action_ai(player, available_actions, engine)
            if chosen_action and chosen_action != GameAction.PASS:
                priority = 3 if chosen_action == GameAction.WIN else (2 if chosen_action == GameAction.GANG else 1)
                actions.append({'player': player, 'action': chosen_action, 'priority': priority})
    
    if not actions:
        return False

    # 找出最高优先级的动作
    max_priority = max(a['priority'] for a in actions)
    best_actions = [a for a in actions if a['priority'] == max_priority]

    # 如果有多个最高优先级的动作，目前简单选择第一个
    # 实际麻将中，胡牌可以有多人，但碰/杠只有一个。我们假设引擎会处理这个逻辑。
    if not best_actions:
        return False
        
    chosen_action_data = best_actions[0]
    actor = chosen_action_data['player']
    action = chosen_action_data['action']
    action_name_map = {
        GameAction.WIN: "胡",
        GameAction.GANG: "杠",
        GameAction.PENG: "碰"
    }
    action_name = action_name_map.get(action, action.value)

    action_tile = format_large_mahjong_tile(engine.last_discarded_tile, color_code="1;35")
    print(f"\n⚡ {actor.name} 决定对 {action_tile} 执行: {action_name}!")
    time.sleep(1)

    success = engine.execute_player_action(actor, action)
    if success:
        if action == GameAction.WIN:
            print(f"✅ {actor.name} 点炮胡牌成功!")
        else:
            print(f"✅ {actor.name} 成功执行 {action_name}!")
        input("\n按回车键继续...") # 为AI响应动作添加暂停
        return True
    else:
        print(f"❌ {actor.name} 执行 {action_name} 失败。")
        return False

def decide_hidden_gang_ai(player: Player, hidden_gang_tiles: List[Tile], engine: GameEngine) -> Tuple[bool, Optional[Tile]]:
    """AI决定是否进行暗杠"""
    if not hidden_gang_tiles:
        return False, None
    
    # 获取AI难度设置
    ai_difficulty = getattr(engine, 'ai_difficulty', 'medium')
    
    # 根据难度决定暗杠概率
    gang_probability = 0.5  # 默认50%概率
    
    if ai_difficulty == "easy":
        gang_probability = 0.3  # 简单AI较少暗杠
    elif ai_difficulty == "medium":
        gang_probability = 0.6  # 中等AI更积极
    elif ai_difficulty == "hard":
        gang_probability = 0.8  # 困难AI非常积极
    else:  # expert
        gang_probability = 0.9  # 专家AI几乎总是暗杠
    
    # 使用概率决定是否暗杠
    import random
    if random.random() < gang_probability:
        # 选择第一个可暗杠的牌
        return True, hidden_gang_tiles[0]
    else:
        return False, None

def choose_best_action_ai(player: Player, available_actions: List[GameAction], engine: GameEngine) -> Optional[GameAction]:
    """AI智能选择最优响应动作"""
    # 使用引擎的统一AI创建方法
    ai = engine.create_ai_instance(player.player_type)
    
    if ai is None:
        # 如果AI创建失败，默认选择过
        return GameAction.PASS
    
    # 构建上下文
    context = {
        "last_discarded_tile": engine.last_discarded_tile,
        "discard_pool": engine.discard_pool,
        "remaining_tiles": engine.deck.get_remaining_count() if engine.deck else 0
    }
    
    # 使用AI算法决定动作
    return ai.decide_action(player, available_actions, context)

def check_response_actions(engine: GameEngine):
    """检查并执行响应动作，获取用户输入"""
    if not engine.last_discarded_tile:
        return False
    
    human_player = engine.get_human_player()
    if not human_player or getattr(human_player, 'is_winner', False):
        return False

    # 在非出牌玩家的回合，才检查响应动作
    if engine.get_current_player() == human_player and engine.get_game_status()['state'] == 'playing':
        return False

    is_sichuan = isinstance(engine.rule, SichuanRule)

    actions_map = {
        "胡": GameAction.WIN,
        "碰": GameAction.PENG,
        "杠": GameAction.GANG,
    }
    if not is_sichuan:
        actions_map["吃"] = GameAction.CHI
    
    possible_actions_str = []
    for name, action in actions_map.items():
        if engine.can_player_action(human_player, action):
            possible_actions_str.append(name)

    if not possible_actions_str:
        return False
    
    response_tile = format_large_mahjong_tile(engine.last_discarded_tile, color_code="1;36")
    print(f"\n⚡ {human_player.name}, 你可以对 {response_tile} 执行的动作: {', '.join(possible_actions_str)}")
    prompt = f"请输入你的选择 ({', '.join(possible_actions_str)}, 或 '过'): "
    
    while True:
        user_choice = input(prompt).strip()
        
        if user_choice == "过":
            print(f"🚫 {human_player.name}选择过")
            engine.execute_player_action(human_player, None)
            return "pass"

        if user_choice in actions_map and user_choice in possible_actions_str:
            action_to_execute = actions_map[user_choice]
            print(f"🔥 {human_player.name}选择{user_choice}!")
            success = engine.execute_player_action(human_player, action_to_execute)
            if success:
                if user_choice == "胡":
                    print(f"✅ {human_player.name} 点炮胡牌成功!")
                else:
                    print(f"✅ {human_player.name} 成功执行{user_choice}!")
                input("\n按回车键继续...") # 为人类玩家响应动作添加暂停
                return True
            else:
                print(f"❌ 执行 {user_choice} 失败。")
        else:
            print("无效的选择，请重新输入。")

def select_game_mode():
    """选择游戏模式"""
    print("\n" + "="*60)
    print("🎮 游戏模式选择")
    print("="*60)
    print("\n📚 训练模式：")
    print("   • AI训练师会提供实时建议和策略指导")
    print("   • 适合学习麻将技巧的新手玩家")
    print("   • 会在关键决策点给出中文提示")
    
    print("\n⚔️  竞技模式：")
    print("   • 与AI对手进行真实对战")
    print("   • 考验你的麻将技巧和策略")
    print("   • 不提供任何提示，完全凭实力")
    
    while True:
        print(f"\n请选择游戏模式:")
        print("  1 - 训练模式 (推荐新手)")
        print("  2 - 竞技模式 (挑战高手)")
        
        choice = input("\n请输入你的选择 (1 或 2): ").strip()
        
        if choice == "1":
            print("✅ 已选择训练模式 - AI训练师将为你提供指导")
            return GameMode.TRAINING
        elif choice == "2":
            print("✅ 已选择竞技模式 - 准备迎接挑战吧！")
            return GameMode.COMPETITIVE
        else:
            print("❌ 无效选择，请输入 1 或 2")

def select_ai_difficulty():
    """选择AI对手难度"""
    print("\n" + "="*60)
    print("🤖 AI对手难度选择")
    print("="*60)
    print("\n🎯 Easy (简单)：")
    print("   • AI决策较为随机，容易出现失误")
    print("   • 适合麻将新手练习基础操作")
    print("   • 流局率较高，游戏节奏相对缓慢")
    
    print("\n⚔️ Medium (中等)：")
    print("   • 使用激进AI策略，积极进攻")
    print("   • 快速决策，降低流局率")
    print("   • 适合有一定经验的玩家")
    
    print("\n🔥 Hard (困难)：")
    print("   • 启用高级AI决策 (MctsAI)\n   • 使用蒙特卡洛树搜索，进行前瞻性决策，显著提升AI强度\n   • 推荐给希望挑战的资深玩家")
    
    print("\n🎯 Expert (专家)：")
    print("   • 使用向听数AI (ShantenAI)")
    print("   • 基于向听数和牌效率理论的高级算法")
    print("   • 采用现代麻将理论，决策更加精准")
    print("   • 推荐给追求极致挑战的高级玩家")
    
    while True:
        print(f"\n请选择AI难度:")
        print("  1 - Easy (简单)")
        print("  2 - Medium (中等)")
        print("  3 - Hard (困难) [已启用]")
        print("  4 - Expert (专家) [向听数AI] [新增]")
        
        choice = input("\n请输入你的选择 (1-4): ").strip()
        
        if choice == "1":
            print("✅ 已选择 Easy 难度 - AI将使用简单策略")
            return "easy"
        elif choice == "2":
            print("✅ 已选择 Medium 难度 - AI将使用激进策略")
            return "medium"
        elif choice == "3":
            print("✅ 已选择 Hard 难度 - AI将使用高级策略")
            return "hard"
        elif choice == "4":
            print("✅ 已选择 Expert 难度 - AI将使用向听数算法")
            return "expert"
        else:
            print("❌ 无效选择，请输入 1、2、3 或 4")

def handle_tile_exchange(engine):
    """处理换三张阶段的人类玩家交互"""
    human_player = engine.get_human_player()
    if not human_player:
        return
    
    print(f"\n🔄 换三张阶段开始！")
    print(f"交换方向: {'顺时针' if engine.exchange_direction == 1 else '逆时针'}")
    print("你需要选择三张同花色的牌进行交换")
    
    # 显示当前手牌
    display_human_hand(engine)
    
    # 按花色分组显示
    suits = {}
    for tile in human_player.hand_tiles:
        if tile.tile_type not in suits:
            suits[tile.tile_type] = []
        suits[tile.tile_type].append(tile)
    
    print("\n📊 按花色分组:")
    suit_names = {"万": "WAN", "筒": "TONG", "条": "TIAO", "风": "FENG", "箭": "JIAN"}
    for suit_type, tiles in suits.items():
        suit_name = suit_type.value
        tiles_display = format_large_mahjong_tiles(tiles, with_indices=False, color_scheme="default")
        print(f"  {suit_name}: {tiles_display} ({len(tiles)}张)")
    
    # 获取AI训练师建议
    if engine.mode == GameMode.TRAINING:
        trainer = TrainerAI()
        advice = trainer.provide_exchange_advice(human_player)
        print(f"\n🎓 AI训练师建议:")
        print(advice)
    
    # 让玩家选择要换的三张牌
    selected_tiles = []
    while len(selected_tiles) != 3:
        print(f"\n请输入要换的三张牌的序号（用空格分隔，如: 1 3 5）:")
        print("注意：必须选择同花色的三张牌")
        
        try:
            choice_str = input(f"请输入三个序号 (1-{len(human_player.hand_tiles)}), 或输入 'r' 重新选择: ")
            
            if choice_str.lower() == 'r':
                selected_tiles = []
                print("已重新开始选择")
                continue
            
            # 解析输入的序号
            choice_parts = choice_str.strip().split()
            if len(choice_parts) != 3:
                print("❌ 请输入恰好三个序号，用空格分隔")
                continue
            
            # 转换为整数并验证
            choice_indices = []
            for part in choice_parts:
                try:
                    idx = int(part) - 1
                    if 0 <= idx < len(human_player.hand_tiles):
                        choice_indices.append(idx)
                    else:
                        print(f"❌ 序号 {part} 无效，请输入1到{len(human_player.hand_tiles)}之间的数字")
                        break
                except ValueError:
                    print(f"❌ '{part}' 不是有效的数字")
                    break
            else:
                # 检查是否有重复的序号
                if len(set(choice_indices)) != 3:
                    print("❌ 不能选择重复的牌，请输入三个不同的序号")
                    continue
                
                # 获取对应的牌
                candidate_tiles = [human_player.hand_tiles[idx] for idx in choice_indices]
                
                # 检查是否为同花色
                first_suit = candidate_tiles[0].tile_type
                if not all(tile.tile_type == first_suit for tile in candidate_tiles):
                    print(f"❌ 必须选择同花色的牌！你选择的牌包含不同花色:")
                    for i, tile in enumerate(candidate_tiles):
                        tile_display = format_large_mahjong_tile(tile, color_code="1;31")
                        print(f"  序号{choice_parts[i]}: {tile_display} ({tile.tile_type.value})")
                    continue
                
                # 选择成功
                selected_tiles = candidate_tiles
                print(f"✅ 已选择三张{first_suit.value}:")
                selected_display = format_large_mahjong_tiles(selected_tiles, with_indices=False, color_scheme="drawn")
                print(f"  {selected_display}")
                break
                
        except Exception as e:
            print(f"❌ 发生错误: {e}")
    
    # 确认选择
    print(f"\n✅ 你选择了以下三张牌进行交换:")
    confirm_display = format_large_mahjong_tiles(selected_tiles, with_indices=True, color_scheme="action")
    print(f"  {confirm_display}")
    
    while True:
        confirm = input("确认交换这三张牌吗？(y/n): ").strip().lower()
        if confirm in ['y', 'yes', '是', '确认']:
            # 提交换牌选择
            success = engine.submit_exchange_tiles(human_player.player_id, selected_tiles)
            if success:
                print("✅ 换牌选择已提交，等待其他玩家...")
                return True
            else:
                print("❌ 换牌提交失败")
                return False
        elif confirm in ['n', 'no', '否', '取消']:
            print("取消选择，重新开始...")
            return handle_tile_exchange(engine)  # 重新开始选择
        else:
            print("请输入 y 或 n")

def main():
    """主演示函数"""
    # 重置终端格式，确保背景一致
    reset_terminal_format()
    
    # 设置终端字体以便更好地显示麻将符号
    set_terminal_font_size()
    
    # 显示游戏横幅
    display_mahjong_banner()
    print("🀄 麻将游戏命令行演示 (血战到底版)")
    if args.debug:
        print("🔧 调试模式已启用 - 日志输出可见")
    else:
        print("🔇 静默模式 - 日志输出已禁用 (使用 --debug 启用)")
    print("=" * 80)

    # 选择游戏模式
    selected_mode = select_game_mode()
    
    # 选择AI难度（仅在竞技模式下）
    if selected_mode == GameMode.COMPETITIVE:
        ai_difficulty = select_ai_difficulty()
    else:
        ai_difficulty = "medium"  # 训练模式默认使用中等难度
    
    # 创建游戏引擎
    engine = GameEngine()
    
    # 设置AI难度属性
    engine.ai_difficulty = ai_difficulty
    
    # 设置游戏模式
    engine.setup_game(selected_mode, "sichuan")
    mode_name = "训练模式" if selected_mode == GameMode.TRAINING else "竞技模式"
    difficulty_name = {"easy": "简单", "medium": "中等", "hard": "困难", "expert": "专家(向听数AI)"}.get(ai_difficulty, "中等")
    
    if selected_mode == GameMode.COMPETITIVE:
        print(f"✅ 游戏设置完成 - {mode_name}，四川麻将，AI难度：{difficulty_name}")
    else:
        print(f"✅ 游戏设置完成 - {mode_name}，四川麻将")
    
    # 开始游戏
    if not engine.start_new_game(): # AI玩家的缺三张和选择缺门同时再游戏引擎内部进行
        print("❌ 游戏启动失败")
        return
    
    print("✅ 游戏开始!")
    
    # 处理换三张阶段
    if engine.state.value == 'tile_exchange':
        print("\n" + "="*60)
        print("🔄 换三张阶段")
        print("="*60)
        
        # 显示游戏状态
        display_game_status(engine)
        display_player_info(engine)
        
        # 记录换牌前的手牌（用于对比）
        human_player = engine.get_human_player()
        original_hand = human_player.hand_tiles.copy() if human_player else []
        
        # 人类玩家选择换牌
        if not handle_tile_exchange(engine):
            print("❌ 换牌失败，游戏结束")
            return
        
        # 等待换牌完成
        while engine.state.value == 'tile_exchange':
            print("⏳ 等待AI玩家完成换牌...")
            import time
            time.sleep(1)
            # AI玩家应该已经自动完成了换牌，这里只是为了确保状态转换
            break
        
        # 显示换牌结果
        if human_player and hasattr(engine, 'received_tiles') and engine.received_tiles:
            received = engine.received_tiles.get(human_player.player_id, [])
            if received:
                print(f"\n🎁 换牌完成！你获得的三张牌:")
                received_str = format_large_mahjong_tiles(received, with_indices=True, color_scheme="drawn")
                print(f"  {received_str}")
                print(f"💡 这些牌来自{'上家' if engine.exchange_direction == -1 else '下家'}玩家")
    
    # 处理选择缺门阶段
    if engine.state.value == 'missing_suit_selection':
        print("\n" + "="*60)
        print("🎲 选择缺门阶段")
        print("="*60)
        
        # 显示换牌后的状态
        display_game_status(engine)
        display_player_info(engine)
        display_human_hand(engine)

        # 交互式选择缺门
        human_player = engine.get_human_player()
        if human_player:
            # 显示各花色统计
            suit_counts = {"万": 0, "筒": 0, "条": 0}
            for tile in human_player.hand_tiles:
                tile_str = str(tile)
                if len(tile_str) >= 2:
                    suit_char = tile_str[-1]
                    if suit_char in suit_counts:
                        suit_counts[suit_char] += 1
            
            print(f"\n📊 你的手牌花色统计:")
            for suit, count in suit_counts.items():
                print(f"  {suit}: {count}张")
            
            # 获取AI训练师建议
            if engine.mode == GameMode.TRAINING:
                trainer = TrainerAI()
                advice = trainer.provide_missing_suit_advice(human_player)
                print(f"\n🎓 AI训练师建议:")
                print(advice)
            
            while not human_player.missing_suit:
                suit_choice = input(f"🎯 {human_player.name}, 请选择缺门 (万, 筒, 条): ").strip()
                if suit_choice in ["万", "筒", "条"]:
                    engine.set_player_missing_suit(human_player, suit_choice)
                    print(f"你选择了缺: {suit_choice}")
                else:
                    print("无效的选择，请输入 '万', '筒', 或 '条'.")

    # AI玩家的缺门选择已由游戏引擎自动处理
    # 等待AI玩家完成选择
    print("⏳ 等待AI玩家完成缺门选择...")
    
    # 显示AI选择结果
    for player in engine.players:
        if player.player_type != PlayerType.HUMAN and player.missing_suit:
            print(f"🎯 {player.name}选择缺{player.missing_suit}")

    # 通知引擎定缺完成，开始打牌阶段
    if engine.state.value != 'playing':
        engine._start_playing()
    
    print("\n" + "="*60)
    if engine.mode == GameMode.TRAINING:
        print("🎮 开始打牌阶段 - 训练模式")
        print("💡 AI训练师将在关键时刻为你提供建议")
    else:
        print("🎮 开始打牌阶段 - 竞技模式")
        print("⚔️ 凭借你的实力与AI对手一决高下！")
    print("="*60)
    
    last_discarder = None
    
    while not engine.is_game_over():
        display_game_status(engine)
        display_player_info(engine)
        display_discard_pool(engine)
        display_human_hand(engine)

        if engine.mode == GameMode.TRAINING:
            get_ai_advice(engine)

        current_player = engine.get_current_player()
        if not current_player:
            print("错误：没有当前玩家。游戏提前结束。")
            break

        if getattr(current_player, 'is_winner', False):
            engine.next_turn()
            continue
        
        game_state = engine.get_game_status()['state']

        # 响应阶段 (有玩家出牌后，等待其他玩家响应)
        if game_state == 'waiting_action' and last_discarder:
            action_taken = False
            human_had_chance_to_act = False
            
            # 1. 检查人类玩家的响应
            human_player = engine.get_human_player()
            if human_player and human_player != last_discarder and not getattr(human_player, 'is_winner', False):
                can_act = any(engine.can_player_action(human_player, act) for act in [GameAction.WIN, GameAction.GANG, GameAction.PENG, GameAction.CHI])
                if can_act:
                    human_had_chance_to_act = True
                    response = check_response_actions(engine)
                    if response is True:
                        action_taken = True
                        last_discarder = None  # 有人响应后重置
            
            # 2. 如果人类玩家未操作，检查AI响应
            if not action_taken:
                if handle_ai_responses(engine, last_discarder):
                    action_taken = True
                    last_discarder = None  # 有人响应后重置
            
            # 3. 如果没有任何人执行动作，并且人类玩家也没有机会去明确地"过"，
            #    那么我们需要手动发送一个"过"指令来推进游戏
            if not action_taken and not human_had_chance_to_act:
                print("所有玩家都选择'过'，游戏继续...")
                # 寻找一个非出牌的玩家来发送"过"指令
                player_to_pass = next((p for p in engine.players if p != last_discarder), None)
                if player_to_pass:
                    engine.execute_player_action(player_to_pass, None)
                last_discarder = None  # 响应阶段结束

            continue # 重新评估游戏状态
        
        # 出牌阶段 - 只有在PLAYING状态且没有响应阶段时才进行
        if game_state == 'playing':
            if current_player.player_type == PlayerType.HUMAN:
                if not simulate_human_turn(engine):
                    break
                last_discarder = current_player
            else:
                if not simulate_ai_turn(engine):
                    break
                last_discarder = current_player
    
    # 游戏结束
    print("\n🎊 游戏结束!")
    
    # 检查是否是流局
    game_state = engine.get_game_state()
    human_player = engine.get_human_player()
    
    if game_state['state'] == 'game_over':
        # 检查是否有胜者
        winners = [p for p in engine.players if getattr(p, 'is_winner', False)]
        if winners:
            for winner in winners:
                print(f"🏆 {winner.name} 胡牌获胜!")
                
            # 根据模式显示不同的结束信息
            if engine.mode == GameMode.TRAINING:
                if human_player in winners:
                    print(f"\n🎉 恭喜！你在训练模式中获得了胜利！")
                    print("💡 继续练习，提升你的麻将技巧！")
                else:
                    print(f"\n📚 这次虽然没有获胜，但这是很好的学习机会！")
                    print("💡 AI训练师的建议有助于提升你的策略水平")
            else:  # 竞技模式
                if human_player in winners:
                    print(f"\n🔥 竞技模式获胜！你展现了真正的麻将实力！")
                    print("⚔️ 恭喜你在没有提示的情况下战胜了AI对手！")
                else:
                    print(f"\n💪 竞技模式失利，但失败是成功之母！")
                    print("🎯 继续挑战，磨练你的麻将技巧！")
        else:
            print("🤝 游戏流局，无人胜出!")
            if engine.mode == GameMode.TRAINING:
                print("💡 流局也是麻将的一部分，继续学习胡牌技巧！")
            else:
                print("⚔️ 势均力敌的对局，下次再来挑战！")
    
    # 显示得分详情
    print("\n💰 本局得分:")
    for player in engine.players:
        score_change = getattr(player, 'last_score_change', 0)
        if score_change > 0:
            print(f"  {player.name}: +{score_change} 分 (总分: {player.score})")
        elif score_change < 0:
            print(f"  {player.name}: {score_change} 分 (总分: {player.score})")
        else:
            print(f"  {player.name}: 0 分 (总分: {player.score})")
    
    display_game_status(engine)
    display_player_info(engine)
    
    # 根据模式显示不同的结束提示
    mode_name = "训练模式" if engine.mode == GameMode.TRAINING else "竞技模式"
    debug_info = " - 调试模式" if args.debug else " - 静默模式"
    ai_difficulty_info = ""
    if hasattr(engine, 'ai_difficulty') and engine.mode == GameMode.COMPETITIVE:
        difficulty_name = {"easy": "简单", "medium": "中等", "hard": "困难"}.get(engine.ai_difficulty, "中等")
        ai_difficulty_info = f", AI难度: {difficulty_name}"
    
    print(f"\n感谢试玩麻将游戏演示！({mode_name}{ai_difficulty_info}{debug_info})")
    print("完整的GUI版本请运行: python3 main.py")
    if not args.debug:
        print("💡 使用 'python3 demo_cli.py --debug' 可查看详细日志信息")
    
    # 程序结束时重置终端格式
    print("\033[0m", end="")

if __name__ == "__main__":
    try:
        main()
    finally:
        # 确保程序退出时重置终端格式
        print("\033[0m", end="") 