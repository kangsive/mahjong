#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麻将游戏命令行演示
"""

import sys
import os
import time

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from game.game_engine import GameEngine, GameMode, GameAction
from game.player import PlayerType
from ai.trainer_ai import TrainerAI
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

def display_player_info(engine):
    """显示所有玩家信息"""
    print("\n📊 玩家信息:")
    
    for i, player in enumerate(engine.players):
        print(f"\n{i+1}. {player.name} ({player.player_type.value})")
        print(f"   手牌数: {player.get_hand_count()}张")
        print(f"   得分: {player.score}")
        
        if player.missing_suit:
            print(f"   缺门: {player.missing_suit}")
        
        if player.melds:
            print(f"   组合: {len(player.melds)}个")
            for meld in player.melds:
                tiles_str = ", ".join(str(t) for t in meld.tiles)
                print(f"     {meld.meld_type.value}: {tiles_str}")
        
        if player.can_win:
            print("   🎉 可以胡牌!")

def display_human_hand(engine):
    """显示人类玩家手牌"""
    human_player = engine.get_human_player()
    if not human_player:
        return
    
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
    context = {
        "can_win": human_player.can_win,
        "last_discarded_tile": engine.last_discarded_tile,
        "is_your_turn": engine.get_current_player() == human_player,
    }
    
    advice = trainer.provide_advice(human_player, context)
    if advice:
        print(f"\n🎓 AI训练师建议:")
        print(advice)

def simulate_human_turn(engine):
    """模拟人类玩家回合"""
    human_player = engine.get_human_player()
    current_player = engine.get_current_player()
    
    if not human_player or current_player != human_player:
        return False
    
    print(f"\n🎮 轮到{human_player.name}了!")
    
    # 显示可选择的牌
    available_tiles = [t for t in human_player.hand_tiles 
                      if engine.rule.can_discard(human_player, t)]
    
    if not available_tiles:
        print("没有可打出的牌!")
        return False
    
    # 简单AI选择（模拟人类选择）
    tile_to_discard = random.choice(available_tiles)
    print(f"选择打出: {tile_to_discard}")
    
    # 执行打牌
    success = engine.execute_player_action(human_player, GameAction.DISCARD, tile_to_discard)
    if success:
        print(f"成功打出 {tile_to_discard}")
        return True
    
    return False

def simulate_ai_turn(engine):
    """模拟AI回合"""
    current_player = engine.get_current_player()
    
    if not current_player or current_player.player_type == PlayerType.HUMAN:
        return False
    
    print(f"\n🤖 {current_player.name}思考中...")
    time.sleep(1)
    
    # AI选择打牌
    available_tiles = [t for t in current_player.hand_tiles 
                      if engine.rule.can_discard(current_player, t)]
    
    if available_tiles:
        tile_to_discard = random.choice(available_tiles)
        print(f"{current_player.name}打出: {tile_to_discard}")
        
        success = engine.execute_player_action(current_player, GameAction.DISCARD, tile_to_discard)
        return success
    
    return False

def check_response_actions(engine):
    """检查响应动作"""
    if not engine.last_discarded_tile:
        return
    
    human_player = engine.get_human_player()
    if not human_player:
        return
    
    actions = []
    if engine.can_player_action(human_player, GameAction.WIN):
        actions.append("胡牌")
    if engine.can_player_action(human_player, GameAction.PENG):
        actions.append("碰")
    if engine.can_player_action(human_player, GameAction.GANG):
        actions.append("杠")
    if engine.can_player_action(human_player, GameAction.CHI):
        actions.append("吃")
    
    if actions:
        print(f"\n⚡ {human_player.name}可以执行的动作: {', '.join(actions)}")
        
        # 简单模拟：随机决定是否执行动作
        if random.random() < 0.3:  # 30%概率执行动作
            if "胡牌" in actions:
                print(f"🎉 {human_player.name}选择胡牌!")
                engine.execute_player_action(human_player, GameAction.WIN)
                return True
            elif "碰" in actions and random.random() < 0.5:
                print(f"🔥 {human_player.name}选择碰!")
                engine.execute_player_action(human_player, GameAction.PENG)
                return True
        
        print(f"🚫 {human_player.name}选择过")
    
    return False

def main():
    """主演示函数"""
    print("🀄 麻将游戏命令行演示")
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
    
    # 设置人类玩家缺门
    human_player = engine.get_human_player()
    if human_player and not human_player.missing_suit:
        missing_suit = "万"  # 简单设置
        engine.set_player_missing_suit(human_player, missing_suit)
        print(f"🎯 {human_player.name}选择缺{missing_suit}")
    
    turn_count = 0
    max_turns = 50  # 限制演示轮数
    
    while not engine.is_game_over() and turn_count < max_turns:
        turn_count += 1
        
        # 显示游戏状态
        display_game_status(engine)
        display_player_info(engine)
        display_human_hand(engine)
        
        # 在训练模式下显示AI建议
        if engine.mode == GameMode.TRAINING:
            get_ai_advice(engine)
        
        # 检查响应动作
        if check_response_actions(engine):
            continue
        
        # 执行当前玩家的回合
        current_player = engine.get_current_player()
        if current_player:
            if current_player.player_type == PlayerType.HUMAN:
                if not simulate_human_turn(engine):
                    break
            else:
                if not simulate_ai_turn(engine):
                    break
        
        # 暂停以便观察
        input("\n按回车键继续...")
    
    # 游戏结束
    if engine.is_game_over():
        print("\n🎊 游戏结束!")
        display_player_info(engine)
    else:
        print(f"\n⏰ 演示结束 (完成{turn_count}轮)")
    
    print("\n感谢试玩麻将游戏演示!")
    print("完整的GUI版本请运行: python3 main.py")

if __name__ == "__main__":
    main() 