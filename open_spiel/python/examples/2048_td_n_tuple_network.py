# Copyright 2023 DeepMind Technologies Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""TD Learning with N-Tuple Networks for 2048"""

from absl import app
from absl import flags
from absl import logging

import numpy as np
import pyspiel

flags.DEFINE_string("game", "2048", "Name of the game.")
flags.DEFINE_integer("num_train_episodes", 15000,
                     "Number of training episodes.")
flags.DEFINE_integer(
    "eval_every", 1000,
    "Episode frequency at which the agent is evaluated.")
FLAGS = flags.FLAGS

n_tuple_size = 6
max_tuple_index = 15
n_tuples = [[0, 1, 2, 3, 4, 5],[4, 5, 6, 7, 8, 9],
    [0, 1, 2, 4, 5, 6],[4, 5, 6, 8, 9, 10],]
n_tuple_network_size = len(n_tuples)

look_up_table_shape = (n_tuple_network_size,) + (max_tuple_index,) * n_tuple_size
look_up_table = np.zeros(look_up_table_shape)
alpha = 0.02

def main(argv):
    game = pyspiel.load_game(FLAGS.game) 
    sum_rewards = 0
    largest_tile = 0
    max_score = 0
    for ep in range(FLAGS.num_train_episodes):
        state = game.new_initial_state()   
        states_in_episode = []            
        while not state.is_terminal():            
            if state.is_chance_node():
                outcomes = state.chance_outcomes()            
                action_list, prob_list = zip(*outcomes)
                action = np.random.choice(action_list, p=prob_list)
                state.apply_action(action)
            else:
                legal_actions = state.legal_actions(state.current_player())
                best_action = max(legal_actions, key=lambda action: evaluator(state, action))
                state.apply_action(best_action)
                states_in_episode.append(state.clone())

        sum_rewards += state.returns()[0]
        largest_tile_from_episode = max(state.observation_tensor(0))
        if (largest_tile_from_episode > largest_tile):
            largest_tile = largest_tile_from_episode
        if (state.returns()[0] > max_score):
            max_score = state.returns()[0]
        
        learn(states_in_episode)
        
        if (ep + 1) % FLAGS.eval_every == 0:
            logging.info(f"[{ep + 1}] Average Score: {int(sum_rewards / FLAGS.eval_every)}, Max Score: {int(max_score)}, Largest Tile Reached: {int(largest_tile)}")            
            sum_rewards = 0
            largest_tile = 0
            max_score = 0

def learn(states):
    target = 0
    while states:
        state = states.pop()
        error = target - value(state)
        target = state.rewards()[0] + update(state, alpha * error)

def update(state, adjust):
    v = 0
    for idx, n_tuple in enumerate(n_tuples):
        v += update_tuple(idx, n_tuple, state, adjust)
    return v

def update_tuple(idx, n_tuple, state, adjust):
    observation_tensor = state.observation_tensor(0)
    index = (idx,) + tuple([0 if observation_tensor[tile] == 0 else int(np.log2(observation_tensor[tile])) for tile in n_tuple])
    look_up_table[index] += adjust
    return look_up_table[index]

def evaluator(state, action):
    working_state = state.clone()
    working_state.apply_action(action)
    return working_state.rewards()[0] + value(working_state)
    
def value(state):
    observation_tensor = state.observation_tensor(0)    
    v = 0
    for idx, n_tuple in enumerate(n_tuples):
        lookup_tuple_index = [0 if observation_tensor[tile] == 0 else int(np.log2(observation_tensor[tile])) for tile in n_tuple]
        lookup_index = (idx,) + tuple(lookup_tuple_index)        
        v += look_up_table[lookup_index]
    return v

if __name__ == "__main__":
  app.run(main)
