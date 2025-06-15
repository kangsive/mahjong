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
from game.player import PlayerType
from ai.trainer_ai import TrainerAI
from rules.sichuan_rule import SichuanRule
import random

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

    # 2. 选择打牌
    available_tiles = [t for t in current_player.hand_tiles 
                      if engine.rule.can_discard(current_player, t)]
    
    if not available_tiles:
        print(f"⚠️ {current_player.name} 无牌可打，游戏可能卡住。")
        return False # 发出错误信号

    tile_to_discard = random.choice(available_tiles)
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

def handle_ai_responses(engine, last_discarder=None):
    """检查并执行AI对出牌的响应动作"""
    if not engine.last_discarded_tile:
        return False

    actions = []
    # 收集所有AI玩家的可能动作
    for player in engine.players:
        if player == last_discarder or player.player_type == PlayerType.HUMAN or getattr(player, 'has_won', False):
            continue

        if engine.can_player_action(player, GameAction.WIN):
            actions.append({'player': player, 'action': GameAction.WIN, 'priority': 3})
        if engine.can_player_action(player, GameAction.GANG):
            actions.append({'player': player, 'action': GameAction.GANG, 'priority': 2})
        if engine.can_player_action(player, GameAction.PENG):
            actions.append({'player': player, 'action': GameAction.PENG, 'priority': 1})
    
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
    
    # 玩家定缺前，先展示手牌
    human_player = engine.get_human_player()
    if human_player and not human_player.missing_suit:
        display_game_status(engine)
        display_player_info(engine)
        display_human_hand(engine)

        # 交互式选择缺门
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
    engine._start_playing()
    
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