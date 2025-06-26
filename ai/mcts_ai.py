# -*- coding: utf-8 -*-
"""
使用蒙特卡洛树搜索（MCTS）的高级AI
"""

import math
import random
import copy
from typing import List, Optional, Dict, Any

from .base_ai import BaseAI
from game.tile import Tile, TileType
from game.player import Player, PlayerType
from game.game_engine import GameEngine, GameAction, GameState

# MCTS 超参数
UCB_C = 2.0  # UCB1算法的探索常数, 增加探索权重

class MctsNode:
    """MCTS树中的节点"""
    def __init__(self, parent: 'MctsNode' = None, action: Any = None, player_id: int = -1):
        self.parent = parent
        self.action = action  # 导致这个状态的动作
        self.children: List['MctsNode'] = []
        self.visits = 0
        self.wins = 0
        self.player_id = player_id
        self.untried_actions: Optional[List[Any]] = None

    def select_child(self) -> 'MctsNode':
        """使用UBC1公式选择最佳子节点"""
        best_child = max(self.children, key=lambda c: (c.wins / c.visits) + UCB_C * math.sqrt(math.log(self.visits) / c.visits))
        return best_child

    def add_child(self, action: Any, player_id: int) -> 'MctsNode':
        """添加一个新的子节点"""
        child = MctsNode(parent=self, action=action, player_id=player_id)
        self.children.append(child)
        return child

    def update(self, result: float):
        """更新节点统计信息"""
        self.visits += 1
        self.wins += result

class MctsAI(BaseAI):
    """使用蒙特卡洛树搜索的AI"""

    def __init__(self, difficulty: str = "hard", engine: Optional[GameEngine] = None):
        super().__init__(difficulty)
        self.engine = engine
        if self.difficulty == "hard":
            self.simulations_per_move = 1500 # 增加模拟次数以提升决策质量
        else: # medium or easy
            self.simulations_per_move = 750

    def choose_discard(self, player: Player, available_tiles: List[Tile]) -> Tile:
        """使用MCTS选择要打出的牌"""
        if not self.engine:
            return random.choice(available_tiles) # Fallback if engine is not provided

        if not available_tiles:
            return player.hand_tiles[-1] if player.hand_tiles else None

        # 如果只有一张牌可打
        if len(available_tiles) == 1:
            return available_tiles[0]

        # MCTS的核心逻辑
        root_node = self._run_mcts(self.engine, available_tiles, is_discard_decision=True, player_id=player.player_id)
        
        # 选择访问次数最多的子节点对应的动作
        if not root_node.children:
            return random.choice(available_tiles)

        best_child = max(root_node.children, key=lambda c: c.visits)
        return best_child.action

    def decide_action(self, player: Player, available_actions: List[GameAction], context: Dict) -> Optional[GameAction]:
        """使用MCTS决定是否碰、杠、胡"""
        if not self.engine:
            # Fallback if engine is not provided
            if GameAction.WIN in available_actions:
                return GameAction.WIN
            return GameAction.PASS
        
        # 总是优先胡牌
        if GameAction.WIN in available_actions:
            return GameAction.WIN

        # 如果只有PASS可选，直接返回
        if len(available_actions) == 1 and GameAction.PASS in available_actions:
            return GameAction.PASS

        # MCTS核心逻辑
        root_node = self._run_mcts(self.engine, available_actions, is_discard_decision=False, player_id=player.player_id)

        # 选择访问次数最多的子节点对应的动作
        if not root_node.children:
            return GameAction.PASS

        best_child = max(root_node.children, key=lambda c: c.visits)
        return best_child.action

    def _run_mcts(self, engine: GameEngine, possible_moves: List[Any], is_discard_decision: bool, player_id: int) -> MctsNode:
        """运行MCTS算法"""
        root_node = MctsNode(player_id=player_id)
        root_node.untried_actions = possible_moves[:]

        for _ in range(self.simulations_per_move):
            sim_engine = copy.deepcopy(engine)
            node = root_node

            # 1. 选择 (Selection)
            while not node.untried_actions and node.children:
                node = node.select_child()
                # 将此动作应用于模拟引擎以到达下一状态
                actor_id = node.parent.player_id
                if 0 <= actor_id < len(sim_engine.players):
                    actor = sim_engine.players[actor_id]
                    action_to_apply = node.action
                    
                    if is_discard_decision:
                        # 对于出牌决策树，所有第一层动作都是当前玩家的出牌动作
                        if 0 <= player_id < len(sim_engine.players):
                            actor = sim_engine.players[player_id]
                    
                    if isinstance(action_to_apply, Tile):
                        sim_engine.execute_player_action(actor, GameAction.DISCARD, action_to_apply)
                    else: # GameAction
                        sim_engine.execute_player_action(actor, action_to_apply)

            # 2. 扩展 (Expansion)
            if node.untried_actions:
                action = random.choice(node.untried_actions)
                node.untried_actions.remove(action)
                
                actor_id = node.player_id
                if 0 <= actor_id < len(sim_engine.players):
                    actor = sim_engine.players[actor_id]
                    
                    # 应用动作
                    if isinstance(action, Tile): # is discard
                        sim_engine.execute_player_action(actor, GameAction.DISCARD, action)
                    else: # is GameAction
                        sim_engine.execute_player_action(actor, action)

                next_player_in_sim = sim_engine.get_current_player()
                child_player_id = next_player_in_sim.player_id if next_player_in_sim else -1
                node = node.add_child(action=action, player_id=child_player_id)

            # 3. 模拟 (Simulation)
            result = self._simulate_random_game(sim_engine, root_node.player_id)
            
            # 4. 反向传播 (Backpropagation)
            while node is not None:
                node.update(result)
                node = node.parent
        
        return root_node

    def _replay_to_node(self, sim_engine: GameEngine, node: MctsNode):
        """此方法已废弃，逻辑合并到 _run_mcts 中"""
        pass

    def _simulate_random_game(self, sim_engine: GameEngine, original_player_id: int) -> float:
        """从当前状态开始进行一次快速的启发式游戏模拟"""
        # 模拟限制，防止无限循环
        for _ in range(150): # 一局游戏通常不会超过150个动作
            if sim_engine.is_game_over():
                break

            current_player = sim_engine.get_current_player()
            if not current_player or getattr(current_player, 'is_winner', False):
                sim_engine.next_turn()
                continue
            
            game_state_val = sim_engine.state.value

            if game_state_val == 'waiting_action':
                # 检查是否有玩家可以响应
                action_taken = False
                for p in sim_engine.players:
                    if p == sim_engine.last_discard_player or getattr(p, 'is_winner', False):
                        continue
                    
                    possible_actions = [act for act in [GameAction.WIN, GameAction.GANG, GameAction.PENG] if sim_engine.can_player_action(p, act)]
                    if possible_actions:
                        # 在模拟中，让AI倾向于执行动作以探索更多可能性
                        if random.random() < 0.75: # 75%的概率执行动作
                            # 优先胡牌
                            chosen_action = GameAction.WIN if GameAction.WIN in possible_actions else random.choice(possible_actions)
                            sim_engine.execute_player_action(p, chosen_action)
                            action_taken = True
                            break # 一次只处理一个响应
                
                if not action_taken:
                    # 如果没有任何人行动，则需要一个玩家来"过"
                    passer = next((p for p in sim_engine.players if p != sim_engine.last_discard_player and not getattr(p, 'is_winner', False)), None)
                    if passer:
                        sim_engine.execute_player_action(passer, None) # None代表PASS
                    else:
                        # 如果找不到passer（例如，只剩一个玩家），让引擎自己推进
                        sim_engine.next_turn()

            elif game_state_val == 'playing':
                # 检查自摸
                if sim_engine.can_player_action(current_player, GameAction.WIN):
                     sim_engine.execute_player_action(current_player, GameAction.WIN)
                     continue

                # 使用启发式方法选择出牌，而不是纯随机
                available_discards = [t for t in current_player.hand_tiles if sim_engine.rule.can_discard(current_player, t)]
                if not available_discards:
                    available_discards = current_player.hand_tiles
                
                if available_discards:
                    discard_tile = self._choose_best_discard_for_simulation(current_player, available_discards)
                    sim_engine.execute_player_action(current_player, GameAction.DISCARD, discard_tile)
                else:
                    # 无法出牌，游戏卡死，结束模拟
                    break
        
        # 游戏结束，评估结果
        winners = [p for p in sim_engine.players if getattr(p, 'is_winner', False)]
        if not winners and sim_engine.is_game_over(): # 流局
            return 0.5
        if any(winner.player_id == original_player_id for winner in winners):
            return 1.0  # 赢了
        elif winners:
            return 0.0 # 输了
        else:
            return 0.2  # 游戏未结束但模拟终止，给一个较低的奖励

    def _choose_best_discard_for_simulation(self, player: Player, available_tiles: List[Tile]) -> Tile:
        """
        在模拟中使用的轻量级出牌选择逻辑。
        借鉴SimpleAI的思路，但更简化以提高速度。
        """
        priorities = []
        for tile in available_tiles:
            priority = 0.0
            
            # 1. 缺门牌最优先
            if player.missing_suit and tile.tile_type.value == player.missing_suit:
                priority += 100
            
            # 2. 孤张字牌优先
            if tile.is_honor_tile():
                count = sum(1 for t in player.hand_tiles if t.value == tile.value and t.tile_type == tile.tile_type)
                if count == 1:
                    priority += 50
            
            # 3. 孤张幺九牌
            if tile.is_terminal():
                count = sum(1 for t in player.hand_tiles if t.value == tile.value and t.tile_type == tile.tile_type)
                if count == 1:
                    priority += 30
            
            # 4. 普通孤张牌
            if tile.is_number_tile() and not tile.is_terminal():
                count = sum(1 for t in player.hand_tiles if t.value == tile.value and t.tile_type == tile.tile_type)
                is_isolated = True
                for t in player.hand_tiles:
                    if t.tile_type == tile.tile_type and abs(t.value - tile.value) <= 2:
                        is_isolated = False
                        break
                if is_isolated and count == 1:
                    priority += 20
            
            priorities.append((tile, priority + random.random())) # 加一点随机性避免总是打同样的牌
            
        if not priorities:
            return random.choice(available_tiles)

        priorities.sort(key=lambda x: x[1], reverse=True)
        return priorities[0][0]

    def choose_missing_suit(self, player: Player) -> str:
        """
        选择缺门（四川麻将）
        MCTS不适合用于此决策，因此我们使用简单AI的逻辑：选择牌数最少的花色。
        """
        suit_counts = {TileType.WAN: 0, TileType.TONG: 0, TileType.TIAO: 0}
        for tile in player.hand_tiles:
            if tile.tile_type in suit_counts:
                suit_counts[tile.tile_type] += 1
        
        # 找出数量最少的花色
        min_suit = min(suit_counts, key=suit_counts.get)
        
        # 从 TileType 枚举值转换为中文字符串
        suit_map = {
            TileType.WAN: "万",
            TileType.TONG: "筒",
            TileType.TIAO: "条"
        }
        return suit_map[min_suit]

    def choose_exchange_tiles(self, player: Player) -> List[Tile]:
        """
        选择换三张的牌
        MCTS不适合用于此决策，使用简单AI的逻辑：选择数量最多的同花色牌中的三张。
        """
        suit_counts = {TileType.WAN: [], TileType.TONG: [], TileType.TIAO: []}
        for tile in player.hand_tiles:
            if tile.tile_type in suit_counts:
                suit_counts[tile.tile_type].append(tile)

        # 过滤掉牌数少于3的花色
        valid_suits = {suit: tiles for suit, tiles in suit_counts.items() if len(tiles) >= 3}

        if not valid_suits:
            # 如果没有任何花色超过3张，则无法完成换牌，这是一个异常情况
            # 随机选择3张牌作为备用方案
            return random.sample(player.hand_tiles, 3)

        # 找到牌数最多的花色
        max_suit = max(valid_suits, key=lambda suit: len(valid_suits[suit]))

        # 从该花色中选择三张牌（例如，选择价值最低的三张）
        tiles_to_exchange = sorted(valid_suits[max_suit], key=lambda t: t.value)[:3]
        
        return tiles_to_exchange 