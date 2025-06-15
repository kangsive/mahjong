#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麻将游戏命令行演示
"""

import sys
import os
import time
# import logging # 日志系统已在此文件中完全禁用

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from game.game_engine import GameEngine, GameMode, GameAction
from game.player import PlayerType, Player
from game.tile import Tile
from ai.trainer_ai import TrainerAI
from rules.sichuan_rule import SichuanRule
import random
from typing import List, Optional

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
    
    discards_str = " ".join(str(t) for t in engine.discard_pool)
    print(f"   {discards_str}")

def display_player_info(engine):
    """显示所有玩家信息"""
    print("\n📊 玩家信息:")
    
    for i, player in enumerate(engine.players):
        status = ""
        # 使用 getattr 安全地访问 has_won 属性
        if getattr(player, 'has_won', False):
            status = "🏆 已胡牌!"
        elif player.can_win:
            status = "🎉 听牌!"

        print(f"\n{i+1}. {player.name} ({player.player_type.value}) {status}")
        
        # 已胡牌的玩家不再显示手牌数，只显示得分和组合
        if getattr(player, 'has_won', False):
            print(f"   得分: {player.score}")
            if player.melds:
                print(f"   组合: {len(player.melds)}个")
                for meld in player.melds:
                    tiles_str = ", ".join(str(t) for t in meld.tiles)
                    print(f"     {meld.meld_type.value}: {tiles_str}")
            continue

        print(f"   手牌数: {player.get_hand_count()}张")
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
                tiles_str = ", ".join(str(t) for t in meld.tiles)
                print(f"     {meld.meld_type.value}: {tiles_str}")

def display_human_hand(engine):
    """显示人类玩家手牌"""
    human_player = engine.get_human_player()
    if not human_player:
        return
    
    # 显示刚摸到的牌
    if (hasattr(engine, 'last_drawn_tile') and engine.last_drawn_tile and 
        engine.get_current_player() == human_player):
        print(f"\n💎 你刚摸到了: {engine.last_drawn_tile}")

    print(f"\n🃏 {human_player.name}的手牌:")
    hand_str = " ".join(f"[{i+1}]{tile}" for i, tile in enumerate(human_player.hand_tiles))
    print(f"   {hand_str}")
    
    if engine.last_discarded_tile:
        print(f"\n💢 最后打出的牌: {engine.last_discarded_tile}")

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

def simulate_human_turn(engine):
    """处理人类玩家的回合，获取用户输入"""
    human_player = engine.get_human_player()
    current_player = engine.get_current_player()

    if not human_player or current_player != human_player:
        return False

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
                    print(f"🚫 规则不允许打出 {tile_to_discard}。请优先打完缺牌。")
                    continue
                
                print(f"你选择了打出: {tile_to_discard}")
                success = engine.execute_player_action(human_player, GameAction.DISCARD, tile_to_discard)
                if success:
                    print(f"✅ 成功打出 {tile_to_discard}")
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

def simulate_ai_turn(engine):
    """模拟AI回合"""
    current_player = engine.get_current_player()
    
    if not current_player or current_player.player_type == PlayerType.HUMAN or getattr(current_player, 'has_won', False):
        return False
    
    print(f"\n🤖 {current_player.name}思考中...")
    time.sleep(1)
    
    # 1. 检查自摸胡牌
    if engine.can_player_action(current_player, GameAction.WIN):
        print(f"🎉 {current_player.name} 决定自摸胡牌!")
        success = engine.execute_player_action(current_player, GameAction.WIN)
        if success:
            print(f"✅ {current_player.name} 成功胡牌!")
            input("\n按回车键继续...")
            return True
        else:
            print(f"❌ {current_player.name} 尝试自摸失败，继续出牌。")

    # 2. 智能选择打牌
    available_tiles = [t for t in current_player.hand_tiles 
                      if engine.rule.can_discard(current_player, t)]
    
    if not available_tiles:
        print(f"⚠️ {current_player.name} 无牌可打，游戏可能卡住。")
        return False # 发出错误信号

    # 使用AI算法选择最优出牌
    tile_to_discard = choose_best_discard_ai(current_player, available_tiles, engine)
    print(f"{current_player.name}打出: {tile_to_discard}")
    
    success = engine.execute_player_action(current_player, GameAction.DISCARD, tile_to_discard)
    if success:
        # 成功出牌后暂停，以便观察
        input("\n按回车键继续...")
        return True
    else:
        # 这是一个严重错误，意味着引擎状态不一致
        print(f"❌ 严重错误: {current_player.name} 无法打出可选牌 {tile_to_discard}.")
        print("   这通常是游戏引擎或规则的内部错误。")
        return False # 发出错误信号

def choose_best_discard_ai(player: Player, available_tiles: List[Tile], engine) -> Tile:
    """AI智能选择最优出牌"""
    from ai.simple_ai import SimpleAI
    from ai.trainer_ai import TrainerAI
    
    # 根据玩家类型选择AI
    if player.player_type == PlayerType.AI_TRAINER:
        ai = TrainerAI()
    else:
        difficulty = "hard" if player.player_type == PlayerType.AI_HARD else "medium"
        ai = SimpleAI(difficulty)
    
    # 使用AI算法选择出牌
    return ai.choose_discard(player, available_tiles)

def handle_ai_responses(engine, last_discarder=None):
    """检查并执行AI对出牌的响应动作"""
    if not engine.last_discarded_tile:
        return False

    actions = []
    # 收集所有AI玩家的可能动作
    for player in engine.players:
        if player == last_discarder or player.player_type == PlayerType.HUMAN or getattr(player, 'has_won', False):
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

    print(f"\n⚡ {actor.name} 决定对 {engine.last_discarded_tile} 执行: {action_name}!")
    time.sleep(1)

    success = engine.execute_player_action(actor, action)
    if success:
        print(f"✅ {actor.name} 成功执行 {action_name}!")
        input("\n按回车键继续...") # 为AI响应动作添加暂停
        return True
    else:
        print(f"❌ {actor.name} 执行 {action_name} 失败。")
        return False

def choose_best_action_ai(player: Player, available_actions: List[GameAction], engine) -> Optional[GameAction]:
    """AI智能选择最优响应动作"""
    from ai.simple_ai import SimpleAI
    from ai.trainer_ai import TrainerAI
    
    # 根据玩家类型选择AI
    if player.player_type == PlayerType.AI_TRAINER:
        ai = TrainerAI()
    else:
        difficulty = "hard" if player.player_type == PlayerType.AI_HARD else "medium"
        ai = SimpleAI(difficulty)
    
    # 构建上下文
    context = {
        "last_discarded_tile": engine.last_discarded_tile,
        "discard_pool": engine.discard_pool,
        "remaining_tiles": engine.deck.get_remaining_count() if engine.deck else 0
    }
    
    # 使用AI算法决定动作
    return ai.decide_action(player, available_actions, context)

def check_response_actions(engine):
    """检查并执行响应动作，获取用户输入"""
    if not engine.last_discarded_tile:
        return False
    
    human_player = engine.get_human_player()
    if not human_player or getattr(human_player, 'has_won', False):
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
    
    print(f"\n⚡ {human_player.name}, 你可以对 {engine.last_discarded_tile} 执行的动作: {', '.join(possible_actions_str)}")
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
                input("\n按回车键继续...") # 为人类玩家响应动作添加暂停
                return True
            else:
                print(f"❌ 执行 {user_choice} 失败。")
        else:
            print("无效的选择，请重新输入。")

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
        print(f"  {suit_name}: {[str(t) for t in tiles]} ({len(tiles)}张)")
    
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
                        print(f"  序号{choice_parts[i]}: {tile} ({tile.tile_type.value})")
                    continue
                
                # 选择成功
                selected_tiles = candidate_tiles
                print(f"✅ 已选择三张{first_suit.value}:")
                for i, tile in enumerate(selected_tiles):
                    print(f"  序号{choice_parts[i]}: {tile}")
                break
                
        except Exception as e:
            print(f"❌ 发生错误: {e}")
    
    # 确认选择
    print(f"\n✅ 你选择了以下三张牌进行交换:")
    for i, tile in enumerate(selected_tiles, 1):
        print(f"  {i}. {tile}")
    
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
    print("🀄 麻将游戏命令行演示 (血战到底版)")
    print("=" * 60)

    # 创建游戏引擎
    engine = GameEngine()
    
    # 设置训练模式
    engine.setup_game(GameMode.TRAINING, "sichuan")
    print("✅ 游戏设置完成 - 训练模式，四川麻将")
    
    # 开始游戏
    if not engine.start_new_game():
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
                for i, tile in enumerate(received, 1):
                    print(f"  {i}. {tile}")
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

    # 为AI玩家自动选择缺门 (四川麻将规则)
    if isinstance(engine.rule, SichuanRule):
        for player in engine.players:
            if player.player_type != PlayerType.HUMAN and not player.missing_suit:
                # 简单AI逻辑: 选择数量最少或没有的花色作为缺门
                suit_counts = {"万": 0, "筒": 0, "条": 0}
                for tile in player.hand_tiles:
                    tile_str = str(tile)
                    if len(tile_str) < 2: continue # Safeguard for unexpected tile formats
                    suit_char = tile_str[-1]
                    if suit_char in suit_counts:
                        suit_counts[suit_char] += 1
                
                missing_suit = min(suit_counts, key=suit_counts.get)
                
                engine.set_player_missing_suit(player, missing_suit)
                print(f"🎯 {player.name}自动选择缺{missing_suit}")

    # 通知引擎定缺完成，开始打牌阶段
    if engine.state.value != 'playing':
        engine._start_playing()
    
    print("\n" + "="*60)
    print("🎮 开始打牌阶段")
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

        if getattr(current_player, 'has_won', False):
            engine.next_turn()
            continue
        
        game_state = engine.get_game_status()['state']

        # 响应阶段 (有玩家出牌后，等待其他玩家响应)
        if game_state == 'waiting_action' and last_discarder:
            action_taken = False
            human_had_chance_to_act = False
            
            # 1. 检查人类玩家的响应
            human_player = engine.get_human_player()
            if human_player and human_player != last_discarder and not getattr(human_player, 'has_won', False):
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
    if game_state['state'] == 'game_over':
        # 检查是否有胜者
        winners = [p for p in engine.players if getattr(p, 'is_winner', False)]
        if winners:
            for winner in winners:
                print(f"🏆 {winner.name} 胡牌获胜!")
        else:
            print("🤝 游戏流局，无人胜出!")
    
    display_game_status(engine)
    display_player_info(engine)
    
    print("\n感谢试玩麻将游戏演示!")
    print("完整的GUI版本请运行: python3 main.py")

if __name__ == "__main__":
    main() 